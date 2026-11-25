# 3일차 작업 기록

날짜: 2026-11-25

## 1단계 준비와 지표 탐색

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| PR 병합 | origin/feat/day2-gateway가 origin/main에 포함 | PR 합쳐짐 (a930823 Merge pull request #2) | 통과 |
| v0.2-day2 태그 | origin에 있음 | refs/tags/v0.2-day2 → a930823 | 통과 |
| 브랜치 | feat/day3-monitoring | main(a930823)에서 생성 | 통과 |
| 스택 4개 상태 | vllm·litellm-db·llm-gateway healthy, litellm Up | 시작 전 4개 모두 Exited(19시간 전). GPU 여유 30314 MiB 확인 후 docker compose start → 약 1.4분(13:10:52 → 13:12:14) 뒤 정상 | 통과 |
| whoami | researcher_a | researcher_a | 통과 |
| chat 200 | 200 | 200, 0.27 s | 통과 |
| vLLM /metrics | 200, 지표 있음 | HTTP 200, 기본 지표 39개(접미사 포함 이름 101개), 핵심 7/7 | 통과 |
| LiteLLM /metrics | 응답 확인 | HTTP 401 (인증 없이 거절) | 확인필요 |
| 게이트웨이 /metrics | 404 (아직 없음) | HTTP 404 | 통과 |
| 포트 9090/3000/9400/9835 | 비어 있음 | 4개 모두 비어 있음 | 통과 |

지표 표

| 컴포넌트 | 지표 이름 | 뜻 | 대시보드 패널 후보 |
|---|---|---|---|
| vLLM | vllm:num_requests_running (gauge) | 지금 배치에서 실행 중인 요청 수 | 동시 처리 요청 수(시계열) |
| vLLM | vllm:num_requests_waiting (gauge) | 대기열에 있는 요청 수 | 대기 요청 수, 0 초과 지속 시 경고 |
| vLLM | vllm:kv_cache_usage_perc (gauge, 1=100%) | KV 캐시 사용률 (gpu_cache_usage_perc는 없음) | KV 캐시 사용률 게이지 |
| vLLM | vllm:e2e_request_latency_seconds (histogram) | 요청 전체 지연 | p50/p95 지연(histogram_quantile) |
| vLLM | vllm:time_to_first_token_seconds (histogram) | 첫 토큰까지 시간(TTFT) | TTFT p95 |
| vLLM | vllm:prompt_tokens_total (counter) | 처리한 입력 토큰 누적 | 입력 토큰/초(rate) |
| vLLM | vllm:generation_tokens_total (counter) | 생성한 출력 토큰 누적 | 출력 토큰/초(rate), 처리량 |
| vLLM | vllm:request_success_total (counter) | 끝난 요청 수(종료 이유 라벨별) | 요청/초, 종료 이유 비율 |
| vLLM | vllm:num_preemptions_total (counter) | KV 부족으로 밀려난 요청 수 | 선점 발생 수(경고) |
| vLLM | vllm:request_queue_time_seconds (histogram) | 대기열에서 기다린 시간 | 대기 시간 p95 |
| vLLM | vllm:inter_token_latency_seconds (histogram) | 토큰 사이 간격 | 토큰 간 지연 p95 |
| LiteLLM | (401로 목록 못 봄) | 인증 필요 | 2단계 이후 결정 |
| 게이트웨이 | (없음, 404) | 지표 엔드포인트 미구현 | 2단계에서 요청 수·상태 코드·지연·PII 건수 추가 |
| GPU | nvidia-smi: utilization.gpu, memory.used, temperature.gpu, power.draw, clocks.sm | GPU 사용률·메모리·온도·전력·클럭 | GPU 사용률·메모리·온도 패널 |

결정 메모
- LiteLLM /metrics는 인증 없이 401이다. 쓰려면 인증 설정(또는 키로 수집)이 필요하므로, 우선 vLLM 지표와 게이트웨이 지표로 대시보드를 만들고 LiteLLM 지표는 보류한다.
- GPU 지표는 3단계에서 dcgm-exporter(포트 9400) 또는 nvidia-smi 기반 수집기(예: 9835) 중에서 고른다. 두 포트 모두 비어 있다.

### 원본 출력

```text
'main' 브랜치로 전환합니다
브랜치가 'origin/main'보다 7개 커밋 뒤에 있고, 앞으로 돌릴 수 있습니다.
  (로컬 브랜치를 업데이트하려면 "git pull"을 사용하십시오)
 create mode 100644 tests/test_masking.py
 create mode 100644 tests/test_proxy.py
To https://github.com/Simon-Beck12/hospital-llm-platform.git
 * [new tag]         v0.2-day2 -> v0.2-day2
새로 만든 'feat/day3-monitoring' 브랜치로 전환합니다
1c6d1ea0ce9e066f20184aca628d3bc7f66ef3ad	refs/tags/v0.2-day2
a9308236c88fa5b55043e2d7827ecd38c8924939	refs/tags/v0.2-day2^{}

$ docker compose ps -a --format '{{.Name}}\t{{.Status}}'
litellm	Exited (0) 19 hours ago
litellm-db	Exited (0) 19 hours ago
llm-gateway	Exited (0) 19 hours ago
vllm	Exited (0) 19 hours ago
$ nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
2293 MiB, 32607 MiB
여유 30314 MiB (기준 28000 이상)
$ date +%T; docker compose start
13:10:52
 Container litellm-db Starting 
 Container vllm Starting 
 Container litellm-db Started 
 Container litellm-db Waiting 
 Container vllm Started 
 Container vllm Waiting 
 Container litellm-db Healthy 
 Container vllm Healthy 
 Container litellm Starting 
 Container litellm Started 
 Container llm-gateway Starting 
 Container llm-gateway Started 
(exit=0)
[13:11:44]
litellm	Up Less than a second
litellm-db	Up 51 seconds (healthy)
llm-gateway	Up Less than a second (health: starting)
vllm	Up 51 seconds (healthy)
[13:12:14]
litellm	Up 30 seconds
litellm-db	Up About a minute (healthy)
llm-gateway	Up 30 seconds (healthy)
vllm	Up About a minute (healthy)
정상 13:12:14

$ curl .../v1/whoami (researcher_a) | jq -c {user_id}
{"user_id":"researcher_a"}
chat -> 200 0.265556s

$ head -1 /tmp/m_*.txt
==> /tmp/m_gw.txt <==
FAIL HTTPError 404

==> /tmp/m_litellm.txt <==
FAIL HTTPError 401

==> /tmp/m_vllm.txt <==
HTTP 200

(vllm:* 지표 이름 목록 101개는 생략, 아래 핵심 지표 표 참조)
$ grep -v '^#' /tmp/m_litellm.txt | grep -oE '^[a-z_]+' | sort -u | head -40
(litellm 지표 이름 수: 0, 줄 수 1)

=== vLLM 핵심 지표 7개 (실제 이름, HELP 첫 줄)
num_requests_running | vllm:num_requests_running | gauge | Number of requests in model execution batches.
num_requests_waiting | vllm:num_requests_waiting | gauge | Number of requests waiting to be processed.
kv_cache_usage_perc | vllm:kv_cache_usage_perc | gauge | KV-cache usage. 1 means 100 percent usage.
e2e_request_latency_seconds | vllm:e2e_request_latency_seconds_bucket | histogram | Histogram of e2e request latency in seconds.
time_to_first_token_seconds | vllm:time_to_first_token_seconds_bucket | histogram | Histogram of time to first token in seconds.
prompt_tokens_total | vllm:prompt_tokens_total | counter | Number of prefill tokens processed.
generation_tokens_total | vllm:generation_tokens_total | counter | Number of generation tokens processed.
=== gpu_cache_usage_perc 존재?
0
=== 기본 지표 이름 수(접미사 제거)
39
=== 현재 값 샘플
vllm:num_requests_running{…} 0.0
vllm:num_requests_waiting{…} 0.0
vllm:kv_cache_usage_perc{…} 0.0
vllm:prompt_tokens_total{…} 13.0
vllm:generation_tokens_total{…} 8.0
vllm:request_success_total{…} 0.0
vllm:request_success_total{…} 1.0
vllm:request_success_total{…} 0.0
=== litellm 응답 원문 1줄
FAIL HTTPError 401
=== gw 응답
FAIL HTTPError 404

$ nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu,power.draw,clocks.sm --format=csv,noheader
1 %, 29576 MiB, 35, 43.56 W, 600 MHz
$ ss -tlnH | awk '{print $4}' | grep -E ':(9090|3000|9400|9835)$' || echo '9090/3000/9400/9835 비어 있음'
9090/3000/9400/9835 비어 있음
```

## 2단계 게이트웨이 /metrics

지표 표

| 이름 | 종류 | 라벨 | 뜻 | 4단계 대시보드 패널 |
|---|---|---|---|---|
| gateway_requests_total | Counter | route, status, user | /v1 요청 수(경로·상태 코드·사용자별) | 사용자별 요청/초, 상태 코드별 비율(4xx·5xx), 429 발생 수 |
| gateway_request_duration_seconds | Histogram (0.05~60초 10구간) | route | 게이트웨이 처리 시간 | 경로별 p50/p95 지연 |
| gateway_tokens_total | Counter | user, kind(prompt·completion) | 사용자별 토큰 수(LiteLLM 응답 usage) | 사용자별 토큰/분, 누적 토큰 |
| gateway_pii_masked_total | Counter | kind(rrn·phone·mrn·email) | 종류별 PII 마스킹 건수 | PII 종류별 건수 |
| gateway_inflight_requests | Gauge | 없음 | 처리 중인 /v1 요청 수 | 동시 요청 수 |

- route는 /v1/chat/completions, /v1/models, /v1/whoami만 그대로 쓰고 나머지는 other다. user는 key_alias, 식별 실패면 unknown이다.
- 라벨에 키, 요청 ID, 프롬프트, IP를 넣지 않는다. 지표 값은 감사 로그 레코드와 같은 값(status, latency_ms, key_alias, usage, pii_counts)으로 갱신한다.
- /metrics와 /healthz는 감사 로그와 요청 지표에 넣지 않는다. /metrics는 인증 없이 열린다(호스트에는 127.0.0.1:18080만 노출).

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| prometheus-client 추가 | uv add, pyproject.toml·uv.lock만 변경 | 0.26.0. 다른 패키지 버전 변경 없음(uv.lock revision 3→5 형식 변경) | 통과 |
| ruff | 오류 0건 | All checks passed (첫 실행 2건: import 순서, except-pass → 수정) | 통과 |
| pytest | 51개 통과 (기존 45 + 새 6) | 51 passed | 통과 |
| 컨테이너 재생성 | gateway만, 3분 이내 healthy | 30초 healthy. vllm·litellm·litellm-db 재시작 없음. 이미지 285MB | 통과 |
| 사용자별 요청 수 | admin·researcher_a·researcher_b status=200 각 1 이상 | 각 1 | 통과 |
| unknown 401 | 1 이상 | route=/v1/models, status=401, user=unknown 1 | 통과 |
| 토큰 | 사용자별 prompt·completion 증가 | 사용자마다 prompt 19, completion 16 | 통과 |
| PII phone | 3 이상 | 3 | 통과 |
| inflight | 0 | 0 | 통과 |
| 키 유출 | 0 | 0 / 0 / 0 | 통과 |
| /metrics 감사 로그 기록 | 0 | 0 | 통과 |

정정: 1단계 보고 세부의 "7개 중 4개"는 틀렸다. 기본 이름 5개 + histogram 2개 = 7개다.

### 원본 출력

```text
$ uv run ruff check .
All checks passed!
(exit=0)

$ uv run pytest -q
51 passed, 1 warning in 0.37s
(exit=0)

$ docker compose up -d --no-deps gateway
 Container llm-gateway Recreate 
 Container llm-gateway Recreated 
 Container llm-gateway Starting 
 Container llm-gateway Started 
[14:09:23] Up Less than a second (health: starting)
[14:09:53] Up 30 seconds (healthy)
$ docker image ls llm-gateway:day2 --format '{{.Size}}'
285MB

admin chat -> 200
researcher_a chat -> 200
researcher_b chat -> 200
키 없음 -> 401
$ curl -s .../metrics | grep -E '^gateway_(requests_total|tokens_total|pii_masked_total|inflight_requests)' | sort
gateway_inflight_requests 0.0
gateway_pii_masked_total{kind="phone"} 3.0
gateway_requests_total{route="/v1/chat/completions",status="200",user="admin"} 1.0
gateway_requests_total{route="/v1/chat/completions",status="200",user="researcher_a"} 1.0
gateway_requests_total{route="/v1/chat/completions",status="200",user="researcher_b"} 1.0
gateway_requests_total{route="/v1/models",status="401",user="unknown"} 1.0
gateway_tokens_total{kind="completion",user="admin"} 16.0
gateway_tokens_total{kind="completion",user="researcher_a"} 16.0
gateway_tokens_total{kind="completion",user="researcher_b"} 16.0
gateway_tokens_total{kind="prompt",user="admin"} 19.0
gateway_tokens_total{kind="prompt",user="researcher_a"} 19.0
gateway_tokens_total{kind="prompt",user="researcher_b"} 19.0
$ curl -s .../metrics | grep -E '^gateway_request_duration_seconds_(count|sum)'
gateway_request_duration_seconds_count{route="/v1/chat/completions"} 3.0
gateway_request_duration_seconds_sum{route="/v1/chat/completions"} 0.708
gateway_request_duration_seconds_count{route="/v1/models"} 1.0
gateway_request_duration_seconds_sum{route="/v1/models"} 0.0
$ 키 3개 grep -cF (/metrics)
0
0
0
```
