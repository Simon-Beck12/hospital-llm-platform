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
