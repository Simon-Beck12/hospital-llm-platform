# 4일차 작업 기록 (2026-11-26)

## 1단계 태그, 기동 확인, 알림 규칙

- 태그: PR #3 병합(66698dd)을 확인했다. main에 `v0.3-day3` 태그를 달고 push했다. 새 브랜치는 `feat/day4-ops`다.
- 기동: `docker compose start` 후 30초 간격으로 확인했다. `compose start` 명령에 약 52초가 걸렸고, 첫 확인 시점(82초)에 7개 모두 running이었다. healthcheck가 있는 3개(litellm-db, llm-gateway, vllm)도 healthy였다. 기동 전 GPU 사용량은 2,752 MiB였다.
- 확인: researcher_a로 chat을 보내 200을 받았다. Prometheus 타깃 4개(gateway, gpu, prometheus, vllm)가 모두 up이었다.
- 마운트: 원래 compose의 prometheus는 `./monitoring/prometheus.yml` 파일 하나만 마운트했다. 그래서 `./monitoring/alerts.yml:/etc/prometheus/alerts.yml:ro` 한 줄을 추가하고 `docker compose up -d --no-deps prometheus`로 prometheus만 다시 만들었다. promdata 볼륨은 그대로다(생성 시각 2026-11-25T14:30:09+09:00로 변화 없음).
- 규칙: [monitoring/alerts.yml](../monitoring/alerts.yml)에 4개를 넣었다. 온도 지표의 실제 이름 `nvidia_smi_temperature_gpu`는 label 값 목록에서 확인했다. 설명은 [alerts.md](alerts.md)에 있다.
- 문법 검사: 프롬프트의 `check config /m/prometheus.yml`은 `"/etc/prometheus/alerts.yml" does not point to an existing file`로 실패했다(컨테이너 기준 경로 때문). `check rules /m/alerts.yml`은 SUCCESS(4 rules)였다. 실제 마운트 경로로 다시 돌린 `check config`도 SUCCESS였다.
- 알림 시험: T0=02:53:37Z에 `docker compose stop vllm`, firing을 2번 연속 확인한 뒤 02:55:23Z에 `docker compose start vllm`.

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 태그 | 원격에 v0.3-day3 | push됨(`[new tag] v0.3-day3`) | 통과 |
| 기동 시간(초) | 5분(300초) 안에 7개 정상 | 82초(30초 간격 첫 확인 시점) | 통과 |
| 타깃 4개 up | 4/4 | 4/4 | 통과 |
| 규칙 4개 ok | 4/4 health ok | 4/4 ok, 모두 inactive | 통과 |
| 지표 보존 | 2026-11-25 06:20Z 값 조회 | `vllm:generation_tokens_total` = 63303 | 통과 |
| firing까지(초) | 3분 안 | 85초(pending 25초) | 통과 |
| 해제까지(초) | vLLM 시작 후 6분 안 | 약 54초(up=1 후 약 13초, 첫 200은 시작 후 45초) | 통과 |

- 시각(UTC, T0 기준): up=0 02:53:49(12초), pending 02:54:02(25초), firing 02:55:02(85초), start 02:55:23(106초), up=1 02:56:04(147초), 첫 200 02:56:08(151초), 해제 약 02:56:17(160초).
- 예상과 다른 점: 허가된 vLLM 중단은 90초였지만 실제 중단(stop → 첫 200)은 151초였다. firing을 기다리는 데만 85초 + 15초 2회 확인이 필요하고, 그 뒤 재기동에 45초가 걸렸기 때문이다.
- 증거: [alert-vllmdown.txt](../evidence/day4/alert-vllmdown.txt)

### 원본 출력

```
$ curl -s 127.0.0.1:9090/api/v1/rules | jq -c '[.data.groups[].rules[] | {name, health, state}]'
[{"name":"VLLMDown","health":"ok","state":"inactive"},{"name":"GatewayDown","health":"ok","state":"inactive"},{"name":"GPUHighTemperature","health":"ok","state":"inactive"},{"name":"KVCacheHigh","health":"ok","state":"inactive"}]

$ curl -s 127.0.0.1:9090/api/v1/targets | jq -c '[.data.activeTargets[] | {job:.labels.job, health}]'
[{"job":"gateway","health":"up"},{"job":"gpu","health":"up"},{"job":"prometheus","health":"up"},{"job":"vllm","health":"up"}]

$ query vllm:generation_tokens_total @ 2026-11-25T06:20:00Z
["63303"]

$ query_range ALERTS{alertname="VLLMDown"} step 1s
pending 2026-11-26T02:54:02Z ~ 2026-11-26T02:55:01Z
firing  2026-11-26T02:55:02Z ~ 2026-11-26T02:56:16Z
```

## 2단계 한도 정책, 텔레메트리, 폐쇄망 시험

- 한도: 키 4개를 각자 자기 키로 `/key/info` 조회했다(마스터 키는 쓰지 않음). 결과는 [key-limits.txt](../evidence/day4/key-limits.txt), 정책은 [quota-policy.md](quota-policy.md)에 있다.
- loadtest 키: 만료 예정 시각은 2026-11-26 06:13:18Z(발급 후 정확히 24시간)다. 03:06Z에는 아직 만료 전이라 chat이 200이었다. 사용자 지시에 따라 만료 시각 기록으로 대체했고, 401 확인은 4일차 5단계 최종 점검으로 미룬다.
- 텔레메트리: compose의 vllm에 `VLLM_NO_USAGE_STATS`, `DO_NOT_TRACK`, `TRANSFORMERS_OFFLINE`를, litellm에 `LITELLM_TELEMETRY`를 추가했다(`HF_HUB_OFFLINE`, `LITELLM_LOCAL_MODEL_COST_MAP`은 원래 있었음). `docker compose up -d --no-deps vllm litellm`으로 다시 만든 뒤 186초 만에 chat 200이 나왔다. 176초 시점은 litellm이 뜨는 중이라 502였다.
- 폐쇄망: [scripts/offline_check.sh](../scripts/offline_check.sh)로 시험했다. 온라인 예행연습은 통과했고, 인자 없이 온라인에서 돌리면 종료 코드 2와 "시험 무효"가 나왔다. 사용자가 유선을 끄고 돌린 결과도 통과였다. 자세한 내용은 [offline.md](offline.md)에 있다.

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 키 한도 일치 | admin 1000/1,000,000, researcher_a 20/20,000, researcher_b 5/2,000, 만료 2026-12-24 전후 | 모두 일치(만료 2026-12-24 04:07Z) | 통과 |
| loadtest 만료 401 | chat 401 | 03:06Z chat 200(만료 예정 06:13:18Z) | 보류(4일차 5단계 최종 점검) |
| 텔레메트리 env 적용 | 6개 | 6개(`docker exec ... env` 확인) | 통과 |
| 온라인 기동(초) | 600초 안에 7개 정상 | 61 | 통과 |
| 오프라인 기동(초) | 600초 안에 7개 정상, 차단 확인 | 61(huggingface와 github DNS 모두 실패) | 통과 |
| 오프라인 chat | 200 | 200(0.334초), whoami 200 | 통과 |

- 외부 접속 로그: 패턴 일치 10줄, 실제 외부 접속 시도 0줄(오탐 분류는 offline.md). 오프라인 시험 후 인터넷을 복구한 뒤에도 github는 200, 컨테이너 7개는 정상, chat은 200이었다.
