# INC-001 vLLM 컨테이너 비정상 종료 (2026-11-25, 재현 훈련)

## 요약

- vLLM 컨테이너를 `docker kill`(SIGKILL)로 강제 종료했다. 재시작 정책(`unless-stopped`)이 동작하지 않아 `docker compose start vllm`으로 수동 복구했다.
- 124초 동안 chat 요청이 실패했다. 사용자는 502가 아니라 500을 받았고, 첫 요청은 60초를 기다린 뒤 504를 받았다.

## 영향

| 항목 | 값 |
|---|---|
| 사용자가 본 오류 코드 | 500 internal_server_error 9건, 504 upstream_timeout 1건(60,004 ms 대기) |
| 오류 응답까지 걸린 시간 | 4.4~60.0초(LiteLLM이 2번 재시도한 뒤 응답) |
| 중단 시간 | 124초(kill 09:55:49 → 첫 200 09:57:53) |
| 영향 범위 | 모든 키의 /v1/chat/completions. /healthz, /metrics, /v1/whoami는 정상 |

## 타임라인

| UTC | KST | 사건 |
|---|---|---|
| 09:55:49 | 18:55:49 | `docker kill vllm` 실행. die exitCode=137 (SIGKILL) |
| 09:55:55 | 18:55:55 | Prometheus `up{job="vllm"}`가 0으로 바뀐 것을 처음 관측 |
| 09:56:04 | 18:56:04 | 클라이언트의 첫 실패: 15초 안에 응답 없음(curl 타임아웃) |
| 09:56:43 | 18:56:43 | 게이트웨이의 첫 오류 응답: 500 (LiteLLM `socket.gaierror` 후 2번 재시도) |
| 09:56:49 | 18:56:49 | kill 시점에 보낸 요청이 504 upstream_timeout(60초)으로 끝남 |
| 09:57:13 | 18:57:13 | 60초 넘게 자동 재시작 없음(RestartCount 0) → `docker compose start vllm` |
| 09:57:49 | 18:57:49 | vllm healthy |
| 09:57:53 | 18:57:53 | 게이트웨이 chat 첫 200 |
| 09:57:55 | 18:57:55 | Prometheus `up{job="vllm"}` = 1 |

## 탐지

- 지표: Prometheus `up{job="vllm"}`가 kill 후 6초 만에 0이 됐다(수집 간격 15초라 최대 15초). Grafana "수집 대상 상태" 패널에서는 vllm이 DOWN으로 보인다.
- 로그: SIGKILL이라 vLLM 로그에는 종료 줄이 없다. 대신 `docker events`에 `die exitCode=137`이 남고, LiteLLM 로그에 `Temporary failure in name resolution`이 찍힌다.
- 탐지까지 6초(지표 기준). 알림 규칙이 없어서 사람에게 알려 주는 수단은 없었다. 이번에는 모니터링 스크립트로 확인했다.
- Grafana "게이트웨이 요청률" 패널의 502 선은 움직이지 않는다. LiteLLM이 연결 실패를 500으로 돌려주기 때문이다.

## 원인

- 직접 원인: vLLM 프로세스가 강제 종료됐다(SIGKILL, exit 137). 실제 운영이라면 OOM killer나 운영자 실수로 생길 수 있다.
- 자동 복구가 안 된 이유: Docker는 `docker kill`처럼 API로 보낸 종료를 수동 중지로 보고, `unless-stopped`여도 재시작하지 않는다. 실제로 84초 동안 exited, RestartCount 0이었다. 반대로 프로세스가 오류로 스스로 끝난 경우(exit 1)에는 재시작 정책이 동작했다(INC-002에서 확인).
- 사용자가 500을 받은 이유: 컨테이너가 멈추면 Docker 내부 DNS에서 `vllm` 이름이 사라진다. 그래서 LiteLLM이 이름 해석에 실패하고, 2번 재시도한 뒤 500을 돌려준다. 게이트웨이는 받은 상태 코드를 그대로 전달한다.

## 조치

```bash
docker kill vllm                 # 장애 재현 (09:55:49)
docker compose start vllm        # 60초 안에 자동 재시작이 없어 수동 복구 (09:57:13)
```

- 재기동에 걸린 시간: start → healthy 36초. torch.compile AOT 캐시를 써서 컴파일은 0.14초였다.

## 재발 방지 (제안, 이번에는 구현 안 함)

1. Prometheus 알림 규칙: `up{job="vllm"} == 0`이 1분 동안 이어지면 알림.
2. 빨리 실패하게 하기: vLLM에 연결할 수 없으면 LiteLLM 재시도를 줄이고, 게이트웨이가 502 upstream_unavailable로 바꿔 돌려준다. 그러면 사용자는 13~60초를 기다리지 않고, 대시보드의 502 선에도 나타난다.
3. 자동 복구 감시: `up == 0`이 1분 넘게 이어지고 컨테이너가 exited이면 `docker compose start vllm`을 실행하는 감시 스크립트를 둔다.

## 증거 파일

- [inc-001-timeline.txt](../../evidence/day3/inc-001-timeline.txt): 10초 간격 상태, HTTP 코드, `up` 값
- [inc-001-logs.txt](../../evidence/day3/inc-001-logs.txt): docker events, vLLM, LiteLLM, 감사 로그의 핵심 줄
