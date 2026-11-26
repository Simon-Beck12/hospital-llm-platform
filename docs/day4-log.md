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

## 3단계 백업과 복구 시험

- 사전 조사: DB 사용자와 DB 이름은 litellm/litellm이다. 볼륨은 `llm-platform_{auditlogs,grafanadata,pgdata}`다. 이미지 postgres:16.16, grafana/grafana:13.3.1, llm-gateway:day2가 모두 로컬에 있다. 행 수는 VerificationToken 4, UserTable 0, SpendLogs 3,157이다.
- 백업: [scripts/backup.sh](../scripts/backup.sh)로 만든 `~/llm-backups/20261126T033123Z`(14초)를 기준으로 쓴다. 첫 실행(`20261126T033045Z`)에서는 Grafana tar의 종료 코드 1("file changed as we read it")을 `&&` 때문에 놓쳤다. 종료 코드 1은 경고(manifest `warnings`), 2 이상은 중단하도록 고쳐 1번 더 돌렸다. 첫 백업 폴더는 지우지 않고 남겨 두었다.
- 복구 시험: [scripts/restore_test.sh](../scripts/restore_test.sh)를 돌렸다. 임시 PostgreSQL은 `--network none`, 임시 Grafana는 127.0.0.1:13000이다. 9개 항목이 모두 일치했고 11초 걸렸다. 끝난 뒤 trap으로 임시 컨테이너 2개와 볼륨 1개를 지웠다.
- 문서: [backup.md](backup.md)

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 권한 700/600 | 폴더 700, 파일 600 | `~/llm-backups`와 백업 폴더 2개 700, 파일 5개 600 | 통과 |
| 덤프 키 0건 | 4개 키 모두 0 | admin 0, loadtest 0, researcher_a 0, researcher_b 0 | 통과 |
| 무결성 | `sha256sum -c` ok | ok | 통과 |
| PG 행 수 3개 | manifest와 같음 | 4/4, 0/0, 3,157/3,157 | 통과 |
| 감사 로그 줄 수 | manifest와 같음 | 3,127/3,127, 첫 줄 JSON(17필드) | 통과 |
| Grafana DB·로그인 | api/health ok, /api/user 200 | ok, 200(grafana.db 1,699,840 B 일치) | 통과 |
| 임시 자원 정리 | restore-test 컨테이너·볼륨 0 | 0 | 통과 |
| 운영 영향 없음 | 7개 정상(재시작 없음), chat 200 | 7개 Up 13분(백업 전부터 계속), chat 200 | 통과 |

## 4단계 README와 확장 설계안

- 백업 폴더 정리: `~/llm-backups/20261126T033045Z`(첫 실행)를 지웠다(사용자 허가). 기준 폴더 `20261126T033123Z`만 남았다.
- [README.md](../README.md)를 다시 썼다. 순서는 한 줄 소개, 핵심 숫자 6개(출처 링크), mermaid 아키텍처, 필수 자격 6개 대응 표, 구성 요소 7개, 빠른 시작 6단계, 운영, 보안 요약, 개발 과정, 한계다.
- [scale-out.md](scale-out.md)는 맨 위에 "설계안, 미구현"을 굵게 적었다. 용량 공식은 3일차 실측(1,620토큰/초, 70% = 약 68,000 TPM)을 쓴다. 30명은 9 GPU, 100명은 30 GPU다(c = 1). "가정" 값은 표에 따로 표시했다.
- [docs/README.md](README.md)는 docs 문서 15개와 evidence 파일 16개의 목차다.

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 백업 폴더 정리 | 20261126T033123Z 1개만 | 1개 | 통과 |
| 자격 6개 매핑 | 6/6, 항목마다 증거 링크 2~3개 | 6/6, 링크 2~4개 | 통과 |
| 링크 깨짐 0 | 상대 링크 전부 존재 | 83개 중 깨짐 0(README, docs/README, scale-out) | 통과 |
| 금지어 0 | <사설IP 대역>, /home/, @gmail, sk- 0건, 기관 이름 0건 | 0건 | 통과 |
| 숫자 출처 일치 | README 숫자마다 출처 문서 | 숫자 32개 모두 출처 있음(git 이력 2개: PR 3개, 태그 3개) | 통과 |

## 5a단계 최종 점검

- 공개 정보 정리: 현재 파일에서 서버 IP, 노트북 IP, 실제 홈 경로를 자리표시자(`<서버IP>`, `<사설IP>`, `~`)로 바꿨다. 파일 3개, 27줄이다(day1-log 22줄, day2-log 4줄, day4-log 1줄). 연구자 계정 경로는 설계 내용이라 그대로 두었다. 4단계 절의 "docs 문서 16개"는 15개로 고쳤다. 이력은 고치지 않았고, 이유는 [security.md](security.md)의 "공개 저장소 정보 노출 관리" 절에 적었다.
- 시연: [scripts/demo.sh](../scripts/demo.sh)(장면 7개)와 [demo.md](demo.md)를 만들었다. 예행 결과는 x-pii-masked 2, researcher_b 6·7회째 429(Retry-After 60초), 규칙 4개 ok였다([demo-dryrun.txt](../evidence/day4/demo-dryrun.txt)).
- 최종 점검: [final-check.txt](../evidence/day4/final-check.txt)

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 테스트·린트·gitleaks | 전부 통과, 0건, 새 건 0 | 53 passed, 0건, no leaks | 통과 |
| 컨테이너 | 7개 정상 | 7개, healthy 3개 | 통과 |
| 포트 | 127.0.0.1에만 | docker 0.0.0.0/::: 0건, ss 4개 모두 127.0.0.1 | 통과 |
| 권한 | .env 600, 키 700/600, 백업 700 | 모두 일치 | 통과 |
| 비밀 파일 추적 | 0건 | 0건 | 통과 |
| 원격 태그 | 3개 | 3개 | 통과 |
| 타깃·규칙·firing | 4 up, 4 ok, 0 | 4, 4, 0 | 통과 |
| 링크 깨짐 | 0 | 134개 중 0 | 통과 |
| 서버 IP·홈 경로 | 0건 | 0건 | 통과 |

- 결과: 최종 점검 16개 항목 중 16개 통과. loadtest 키 401 확인과 태그는 5b단계에서 한다.
