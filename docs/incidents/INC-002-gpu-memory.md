# INC-002 GPU 메모리 부족으로 vLLM 기동 실패 (2026-11-25, 재현 훈련)

## 요약

- 다른 프로세스(gpu-hog)가 GPU 메모리 10,738 MiB를 잡고 있는 상태에서 vLLM을 기동했다. 여유 메모리 18.21 GiB가 필요량 26.62 GiB(전체 × 0.85)보다 적어서 기동에 실패했다.
- gpu-hog를 지우자 재시작 정책으로 자동 재기동됐다. 삭제하고 23초 뒤 200이 나왔다.

## 영향

| 항목 | 값 |
|---|---|
| 사용자가 본 오류 코드 | 500 internal_server_error 5건(측정 요청 전부, 응답까지 4.5~5.0초) |
| 중단 시간 | 101초(기동 시도 09:59:31 → 첫 200 10:01:12). 계획된 정지(09:58:46)부터 따지면 146초 |
| 영향 범위 | 모든 키의 /v1/chat/completions |

## 타임라인

| UTC | KST | 사건 |
|---|---|---|
| 09:58:46 | 18:58:46 | `docker compose stop vllm`(계획된 정지). GPU 사용량 29,455 → 2,028 MiB |
| 09:58:51 | 18:58:51 | gpu-hog 시작. 09:59:22에 10,738 MiB 점유 확인 |
| 09:59:31 | 18:59:31 | T1 `docker compose start vllm` |
| 09:59:36 | 18:59:36 | 게이트웨이 chat 첫 500 응답(4.5초 소요) |
| 09:59:49 | 18:59:49 | vLLM `ValueError: Free memory on device cuda:0 (18.21/31.31 GiB) ... less than desired GPU memory utilization (0.85, 26.62 GiB)` |
| 09:59:53 | 18:59:53 | die exitCode=1 → 자동 재시작(`unless-stopped`) |
| 10:00:14, 10:00:36 | 19:00:14, 19:00:36 | 같은 오류로 다시 die와 재시작(약 21초 간격) |
| 10:00:49 | 19:00:49 | `docker rm -f gpu-hog` |
| 10:01:04 | 19:01:04 | 3번째 재시작이 메모리 점검을 통과함. `Available KV cache memory: 10.1 GiB` |
| 10:01:12 | 19:01:12 | vllm healthy, 게이트웨이 chat 첫 200 |
| 10:01:25 | 19:01:25 | Prometheus `up{job="vllm"}` = 1 |

## 탐지

- 로그: T1 후 18초에 vLLM 로그에 `ValueError: Free memory ...`가 찍혔다. 원인(여유 메모리, 필요량)이 숫자로 바로 나온다.
- 컨테이너: `docker events`에서 die exitCode=1이 약 21초마다 반복됐고, RestartCount가 0 → 3으로 늘었다.
- 지표: 계획된 정지 때부터 `up{job="vllm"}`가 0이었다. 그래서 지표만으로는 "기동 중"인지 "기동 실패"인지 구분할 수 없다. healthcheck도 "starting"으로만 보인다.
- 탐지까지 18초(로그 기준).

## 원인

- vLLM은 시작할 때 GPU 여유 메모리가 `전체 × gpu_memory_utilization` 이상인지 확인한다.
- 필요량은 32,607 MiB × 0.85 = 27,715 MiB(26.62 GiB)였다. 여유는 19,318 MiB(18.21 GiB)로 8,397 MiB 모자랐다.
- 부족해진 이유는 gpu-hog 컨테이너(python3, torch.empty 10GiB)가 10,738 MiB를 잡고 있었기 때문이다. 실제 운영이라면 같은 GPU에 남은 노트북이나 학습 프로세스가 이렇게 메모리를 잡을 수 있다.
- vLLM을 기동하려면 다른 프로세스의 GPU 사용량이 전체 × 0.15 = 4,891 MiB 이하여야 한다. 평소 다른 프로세스 사용량은 2,028 MiB다.

## 조치

```bash
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv   # 점유 프로세스 확인
docker ps --filter name=gpu-hog                                               # 점유 컨테이너 확인
docker rm -f gpu-hog                                                          # 점유 해제 (10:00:49)
docker inspect -f '{{.State.Status}} {{.RestartCount}}' vllm                  # running 3: 재시작 중이라 start 생략
```

- vLLM 설정(gpu-memory-utilization 0.85)은 바꾸지 않았다. 다른 프로세스를 없애는 것으로 복구했다.
- 복구 후 GPU 사용량은 29,303 MiB로, 기준(29,455 MiB)과 152 MiB 차이다.

## 재발 방지 (제안, 이번에는 구현 안 함)

1. 기동 전 점검 스크립트: `nvidia-smi`의 여유 메모리가 `전체 × 0.85 + 여유분`보다 적으면 기동을 멈추고, 점유 프로세스 목록을 출력한다.
2. 재시작 반복 알림: vllm 컨테이너의 재시작 횟수가 5분에 2회 이상 늘거나 `up{job="vllm"} == 0`이 3분 넘게 이어지면 알림을 보낸다. 3분은 기동에 걸리는 시간(약 40초)을 감안한 값이다.
3. GPU 사용 규칙: 서빙용 GPU에는 vLLM 말고 다른 연산 프로세스를 띄우지 않는다. 가능하면 `nvidia_smi` 지표로 vLLM 밖의 메모리 사용이 4,891 MiB를 넘을 때 알림을 보낸다.

## 증거 파일

- [inc-002-timeline.txt](../../evidence/day3/inc-002-timeline.txt): 상태, HTTP 코드, `up` 값, docker events
- [inc-002-logs.txt](../../evidence/day3/inc-002-logs.txt): vLLM의 ValueError 줄, die와 재시작 기록
- [inc-002-diagnosis.txt](../../evidence/day3/inc-002-diagnosis.txt): nvidia-smi 프로세스 목록, gpu-hog, 계산식
