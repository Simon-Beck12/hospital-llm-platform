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

## 3단계 Prometheus와 GPU 지표

구성 표

| 서비스 | 이미지 | 호스트 포트 | 수집 대상 |
|---|---|---|---|
| prometheus | prom/prometheus:v3.15.1 | 127.0.0.1:9090 | localhost:9090, vllm:8000, gateway:8080, gpu-exporter:9835 (15초 간격) |
| gpu-exporter | utkuozdemir/nvidia_gpu_exporter:1.17.0 | 없음(backend 내부망만) | nvidia-smi 값을 :9835/metrics로 내보냄 |
| (수집됨) vllm | vllm/vllm-openai:v0.33.0 | 없음 | vllm:* 지표 |
| (수집됨) gateway | llm-gateway:day2 | 127.0.0.1:18080 | gateway_* 지표 |

- 보존: --storage.tsdb.retention.time=15d, --storage.tsdb.retention.size=5GB, promdata 볼륨.
- LiteLLM 지표는 수집하지 않는다(/metrics 401, 1단계 결정).

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| promtool | check config SUCCESS | SUCCESS | 통과 |
| compose 문법 | config --quiet OK, 추가만 | OK, 34줄 추가·삭제 0 | 통과 |
| 컨테이너 6개 | 6개 Up | vllm, litellm-db, litellm, llm-gateway, prometheus, gpu-exporter. 기존 4개 재시작 없음 | 통과 |
| gpu-exporter nvidia-smi | GPU 0: RTX 5090 | GPU 0: NVIDIA GeForce RTX 5090 | 통과 |
| 수집 대상 | 4/4 up | prometheus, vllm, gateway, gpu 모두 up, lastError 없음 | 통과 |
| 사용자별 요청 수 | 쿼리 결과 있음 | admin 2, researcher_a 2, researcher_b 2, unknown 1 | 통과 |
| KV cache 값 | 쿼리 결과 있음 | 0 (유휴, 요청 끝난 뒤 조회) | 통과 |
| p95 지연 | 쿼리 결과 있음 | 0.2425 s (5분 rate) | 통과 |
| GPU 지표 5종 | 사용률·메모리 사용·메모리 전체·온도·전력 | 0.07(7%), 28.71 GiB, 31.84 GiB, 45℃, 87.29 W | 통과 |
| uv 호환 | 로컬 uv와 Dockerfile uv 같음, revision 5로 빌드 성공 | 로컬 uv 0.13.6 = Dockerfile uv:0.13.6, uv.lock revision 5, 이미지 2026-11-25 14:09 빌드 성공 | 통과 |
| 호스트 포트 | 9090만 127.0.0.1, 9835 비노출 | 127.0.0.1:9090만 LISTEN | 통과 |

4단계 대시보드용 PromQL

| 패널 | PromQL |
|---|---|
| 수집 상태 | `up` |
| 동시 처리 요청(vLLM) | `vllm:num_requests_running` |
| 대기 요청(vLLM) | `vllm:num_requests_waiting` |
| KV 캐시 사용률 | `vllm:kv_cache_usage_perc * 100` |
| 사용자별 요청 수 | `sum by (user) (gateway_requests_total)` |
| 사용자별 요청/초 | `sum by (user) (rate(gateway_requests_total[5m]))` |
| 상태 코드별 요청/초 | `sum by (status) (rate(gateway_requests_total[5m]))` |
| 사용자별 토큰 | `sum by (user, kind) (gateway_tokens_total)` |
| 게이트웨이 p95 지연 | `histogram_quantile(0.95, sum by (le) (rate(gateway_request_duration_seconds_bucket[5m])))` |
| vLLM TTFT p95 | `histogram_quantile(0.95, sum by (le) (rate(vllm:time_to_first_token_seconds_bucket[5m])))` |
| PII 종류별 건수 | `sum by (kind) (gateway_pii_masked_total)` |
| GPU 사용률 | `nvidia_smi_utilization_gpu_ratio * 100` |
| GPU 메모리 | `nvidia_smi_memory_used_bytes / 1024^3`, `nvidia_smi_memory_total_bytes / 1024^3` |
| GPU 온도 | `nvidia_smi_temperature_gpu` |
| GPU 전력 | `nvidia_smi_power_draw_watts` |

메모
- GPU 지표 실제 이름: nvidia_smi_utilization_gpu_ratio(0~1), nvidia_smi_memory_used_bytes, nvidia_smi_memory_total_bytes, nvidia_smi_temperature_gpu, nvidia_smi_power_draw_watts(average·instant 변형도 있음).
- 사용자별 요청 수 2는 2단계 확인 요청 1건과 이번 요청 1건의 합이다(gateway 재생성 이후 누적).

### 원본 출력

```text
$ uv --version
uv 0.13.6 (x86_64-unknown-linux-gnu)
$ grep -m1 'ghcr.io/astral-sh/uv' Dockerfile
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /bin/uv
$ head -3 uv.lock
version = 1
revision = 5
requires-python = ">=3.12"
$ docker image inspect llm-gateway:day2 --format '{{.Created}}'
2026-11-25T14:09:18.735782768+09:00

$ docker run --rm -v "$PWD/monitoring:/cfg:ro" --entrypoint promtool prom/prometheus:v3.15.1 check config /cfg/prometheus.yml
Checking /cfg/prometheus.yml
 SUCCESS: /cfg/prometheus.yml is valid prometheus config file syntax

(exit=0)
$ docker compose config --quiet && echo "compose 문법 OK"
compose 문법 OK
$ git diff --numstat compose.yaml
34	0	compose.yaml
삭제 줄: 0

$ docker compose up -d --no-deps prometheus gpu-exporter
 Image utkuozdemir/nvidia_gpu_exporter:1.17.0 Pulled 
 Volume llm-platform_promdata Creating 
 Volume llm-platform_promdata Creating 
 Container gpu-exporter Creating 
 Volume llm-platform_promdata Created 
 Volume llm-platform_promdata Created 
 Container prometheus Creating 
 Container prometheus Created 
 Container gpu-exporter Created 
 Container prometheus Starting 
 Container gpu-exporter Starting 
 Container prometheus Started 
 Container gpu-exporter Started 
(exit=0)
$ docker compose ps --format '{{.Name}}\t{{.Status}}'
gpu-exporter	Up 5 seconds
litellm	Up About an hour
litellm-db	Up About an hour (healthy)
llm-gateway	Up 20 minutes (healthy)
prometheus	Up 5 seconds
vllm	Up About an hour (healthy)
$ docker compose exec gpu-exporter nvidia-smi -L
GPU 0: NVIDIA GeForce RTX 5090 (UUID: GPU-138dd643-d4bb-f97d-9b26-d9c05720b67a)
(exit=0)

$ curl -s http://127.0.0.1:9090/api/v1/targets | jq -r '.data.activeTargets[] | "\(.labels.job)\t\(.health)\t\(.lastError)"'
gateway	up	
gpu	up	
prometheus	up	
vllm	up	

$ Q 'up'
[{"m":{"__name__":"up","instance":"gpu-exporter:9835","job":"gpu"},"v":"1"},{"m":{"__name__":"up","instance":"vllm:8000","job":"vllm"},"v":"1"},{"m":{"__name__":"up","instance":"gateway:8080","job":"gateway"},"v":"1"},{"m":{"__name__":"up","instance":"localhost:9090","job":"prometheus"},"v":"1"}]
$ Q 'vllm:num_requests_running'
[{"m":{"__name__":"vllm:num_requests_running","engine":"0","instance":"vllm:8000","job":"vllm","model_name":"qwen3-8b"},"v":"0"}]
$ Q 'vllm:kv_cache_usage_perc'
[{"m":{"__name__":"vllm:kv_cache_usage_perc","engine":"0","instance":"vllm:8000","job":"vllm","model_name":"qwen3-8b"},"v":"0"}]
$ Q 'sum by (user) (gateway_requests_total)'
[{"m":{"user":"admin"},"v":"2"},{"m":{"user":"researcher_a"},"v":"2"},{"m":{"user":"researcher_b"},"v":"2"},{"m":{"user":"unknown"},"v":"1"}]
$ Q 'sum by (user, kind) (gateway_tokens_total)'
[{"m":{"kind":"prompt","user":"admin"},"v":"32"},{"m":{"kind":"completion","user":"admin"},"v":"32"},{"m":{"kind":"prompt","user":"researcher_a"},"v":"32"},{"m":{"kind":"completion","user":"researcher_a"},"v":"32"},{"m":{"kind":"prompt","user":"researcher_b"},"v":"32"},{"m":{"kind":"completion","user":"researcher_b"},"v":"32"}]
$ Q 'histogram_quantile(0.95, sum by (le) (rate(gateway_request_duration_seconds_bucket[5m])))'
[{"m":{},"v":"0.2425"}]
$ GPU 지표 이름
nvidia_smi_memory_total_bytes
nvidia_smi_memory_used_bytes
nvidia_smi_power_draw_average_watts
nvidia_smi_power_draw_instant_watts
nvidia_smi_power_draw_watts
nvidia_smi_temperature_gpu
nvidia_smi_temperature_gpu_tlimit
nvidia_smi_utilization_gpu_ratio
$ Q 'nvidia_smi_memory_total_bytes'
[{"m":{"__name__":"nvidia_smi_memory_total_bytes","instance":"gpu-exporter:9835","job":"gpu","uuid":"138dd643-d4bb-f97d-9b26-d9c05720b67a"},"v":"34190917632"}]
$ Q 'nvidia_smi_memory_used_bytes'
[{"m":{"__name__":"nvidia_smi_memory_used_bytes","instance":"gpu-exporter:9835","job":"gpu","uuid":"138dd643-d4bb-f97d-9b26-d9c05720b67a"},"v":"30832328704"}]
$ Q 'nvidia_smi_power_draw_average_watts'
[{"m":{"__name__":"nvidia_smi_power_draw_average_watts","instance":"gpu-exporter:9835","job":"gpu","uuid":"138dd643-d4bb-f97d-9b26-d9c05720b67a"},"v":"87.29"}]
$ Q 'nvidia_smi_power_draw_instant_watts'
[{"m":{"__name__":"nvidia_smi_power_draw_instant_watts","instance":"gpu-exporter:9835","job":"gpu","uuid":"138dd643-d4bb-f97d-9b26-d9c05720b67a"},"v":"90.01"}]
$ Q 'nvidia_smi_power_draw_watts'
[{"m":{"__name__":"nvidia_smi_power_draw_watts","instance":"gpu-exporter:9835","job":"gpu","uuid":"138dd643-d4bb-f97d-9b26-d9c05720b67a"},"v":"87.29"}]
$ Q 'nvidia_smi_temperature_gpu'
[{"m":{"__name__":"nvidia_smi_temperature_gpu","instance":"gpu-exporter:9835","job":"gpu","uuid":"138dd643-d4bb-f97d-9b26-d9c05720b67a"},"v":"45"}]
$ Q 'nvidia_smi_temperature_gpu_tlimit'
[{"m":{"__name__":"nvidia_smi_temperature_gpu_tlimit","instance":"gpu-exporter:9835","job":"gpu","uuid":"138dd643-d4bb-f97d-9b26-d9c05720b67a"},"v":"45"}]
$ Q 'nvidia_smi_utilization_gpu_ratio'
[{"m":{"__name__":"nvidia_smi_utilization_gpu_ratio","instance":"gpu-exporter:9835","job":"gpu","uuid":"138dd643-d4bb-f97d-9b26-d9c05720b67a"},"v":"0.07"}]
```

## 4단계 Grafana 대시보드

대시보드 "LLM 플랫폼 운영"(uid llm-platform, 폴더 LLM Platform, 새로고침 10s, 기본 범위 지난 30분). 데이터소스·대시보드는 모두 프로비저닝 파일로 올렸다(UI 수정 불가, allowUiUpdates false).

패널 표 (쿼리 결과: 트래픽 후 Prometheus 즉시 쿼리, $__range → 30m)

| 번호 | 행 | 제목 | PromQL | 단위 | 쿼리 결과 |
|---|---|---|---|---|---|
| 1 | 서비스 상태 | 수집 대상 상태(stat, 1=UP 초록, 0=DOWN 빨강) | `up` | none | 있음 (4개 모두 1) |
| 2 | 서비스 상태 | vLLM 대기열 | `vllm:num_requests_running`, `vllm:num_requests_waiting` | short | 있음 (0, 0) |
| 3 | 서비스 상태 | 게이트웨이 진행 중 요청(stat) | `gateway_inflight_requests` | short | 있음 (0) |
| 4 | 지연과 처리량 | 게이트웨이 요청률(상태 코드별) | `sum by (status) (rate(gateway_requests_total[1m]))` | reqps | 있음 (200: 0.111) |
| 5 | 지연과 처리량 | 게이트웨이 지연 p50/p95 | `histogram_quantile(0.5\|0.95, sum by (le) (rate(gateway_request_duration_seconds_bucket[5m])))` | s | 있음 (0.182 / 0.416) |
| 6 | 지연과 처리량 | vLLM 첫 토큰 지연 p95 | `histogram_quantile(0.95, sum by (le) (rate(vllm:time_to_first_token_seconds_bucket[5m])))` | s | 있음 (0.028) |
| 7 | 지연과 처리량 | vLLM 전체 지연 p95 | `histogram_quantile(0.95, sum by (le) (rate(vllm:e2e_request_latency_seconds_bucket[5m])))` | s | 있음 (0.285) |
| 8 | 지연과 처리량 | 생성 처리량 | `rate(vllm:generation_tokens_total[1m])` | tok/s (suffix) | 있음 (0.889) |
| 9 | 사용자와 보안 | 사용자별 요청 수(bargauge) | `sum by (user) (increase(gateway_requests_total[$__range]))` | short | 있음 (admin 11.2, researcher_a 11.2, researcher_b 6.1, unknown 0) |
| 10 | 사용자와 보안 | 사용자별 토큰(bargauge) | `sum by (user) (increase(gateway_tokens_total[$__range]))` | short | 있음 (admin 529, researcher_a 529, researcher_b 137) |
| 11 | 사용자와 보안 | 사용자별 429(bargauge) | `sum by (user) (increase(gateway_requests_total{status="429"}[$__range]))` | short | 있음, 단 값 0 (실제 2건, 아래 메모) |
| 12 | 사용자와 보안 | PII 마스킹 건수(종류별, bargauge) | `sum by (kind) (increase(gateway_pii_masked_total[$__range]))` | short | 있음 (phone 20.4) |
| 13 | GPU | GPU 사용률 | `nvidia_smi_utilization_gpu_ratio * 100` | percent | 있음 (4) |
| 14 | GPU | GPU 메모리 | `nvidia_smi_memory_used_bytes / 1024^3`, `nvidia_smi_memory_total_bytes / 1024^3` | gbytes(GiB) | 있음 (28.72 / 31.84) |
| 15 | GPU | GPU 온도·전력(왼쪽 ℃, 오른쪽 W) | `nvidia_smi_temperature_gpu`, `nvidia_smi_power_draw_watts` | celsius / watt | 있음 (40 / 61.99) |
| 16 | GPU | KV 캐시 사용률(gauge 0~100, 80 노랑, 95 빨강) | `vllm:kv_cache_usage_perc * 100` | percent | 있음 (0) |

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| compose 문법 | OK, 추가만 | OK, 26줄 추가·삭제 0 | 통과 |
| health | database ok, 2분 이내 | ok, 약 20초 (13.3.1). 기존 6개 재시작 없음 | 통과 |
| 데이터소스 | 1개, uid prometheus | Prometheus / prometheus / http://prometheus:9090, health OK | 통과 |
| 패널 16 | 16 | 16 (행 4, 단위 없는 패널 0) | 통과 |
| 폴더 | LLM Platform | LLM Platform | 통과 |
| 익명 401 | 401 | 401. 가입 꺼짐(disableUserSignUp true), 익명 꺼짐, 가입 API 401 | 통과 |
| 결과 있는 패널 수 | 14 이상 | 16/16 | 통과 |
| .env 600 | 600 | 600 (GRAFANA_ADMIN_PASSWORD 1줄 추가, 19 → 20줄) | 통과 |
| 비밀번호 유출 0 | 0 | 0 (git grep, gitleaks) | 통과 |
| 호스트 포트 | 127.0.0.1:3000만 | 127.0.0.1:3000 LISTEN | 통과 |

메모
- 사용자별 429 패널이 0으로 나온다. researcher_b 429 시계열이 처음 수집될 때 이미 값이 2였고(counter를 0으로 미리 만들지 않음), increase()는 첫 표본 이전 증가를 세지 않는다. raw counter `gateway_requests_total{status="429"}`는 2, unknown 401도 같은 이유로 increase 0이다.
  고치려면 (a) 게이트웨이가 알려진 사용자·상태 조합을 0으로 미리 만들거나, (b) 패널 쿼리를 raw counter 또는 `increase(...) or 현재값` 형태로 바꿔야 한다. 이번 단계에서는 바꾸지 않았다.
- increase()는 구간 끝을 외삽해서 정수가 아닌 값(11.222 등)이 나온다. bargauge 소수점은 0자리로 표시한다.
- KV 캐시 부하 시 값은 5단계 Locust에서 확인한다.
- Grafana 비밀번호는 .env에만 있고, API 확인은 권한 600 임시 netrc 파일로만 넘긴 뒤 지웠다.

### 원본 출력

```text
$ stat -c '%a' .env
600
.env 줄 수: 19 → 20
GRAFANA_ADMIN_PASSWORD 줄 수: 1 (32자 값)

$ jq '.panels | map(select(.type != "row")) | length'
16
$ jq -e '.uid == "llm-platform"'
true
행 수: 4
단위 없는 패널: 0

$ docker compose config --quiet && echo "compose 문법 OK"
compose 문법 OK
$ git diff --numstat compose.yaml
26	0	compose.yaml
삭제 줄: 0

$ docker compose up -d --no-deps grafana
 Image grafana/grafana:13.3.1 Pulled 
 Volume llm-platform_grafanadata Creating 
 Volume llm-platform_grafanadata Creating 
 Volume llm-platform_grafanadata Created 
 Volume llm-platform_grafanadata Created 
 Container grafana Creating 
 Container grafana Created 
 Container grafana Starting 
 Container grafana Started 
[14:45:28] 응답 없음
[14:45:38] 응답 없음
[14:45:48] {  "database": "ok",  "version": "13.3.1",  "commit": "da3aa3ff574e7dbbf808c66b6daa744defed0441"}
ok=1

$ curl -s --netrc-file "$NETRC" .../api/datasources | jq -c "map({name, uid, url})"
[{"name":"Prometheus","uid":"prometheus","url":"http://prometheus:9090"}]
$ curl -s --netrc-file "$NETRC" .../api/dashboards/uid/llm-platform | jq -c {title, panels, folder}
{"title":"LLM 플랫폼 운영","panels":16,"folder":"LLM Platform"}
익명 접근 -> 401
$ 데이터소스 상태 확인 (health)
{"status":"OK","message":"Successfully queried the Prometheus API."}
$ 가입·익명 설정
{"disableUserSignUp":true,"anonymousEnabled":false}
가입 API(익명) -> 401

$ 트래픽: admin·researcher_a 각 10회 chat(max_tokens 64, 전화번호 포함)
응답 코드:      20 200 
$ sleep 61; researcher_b 7회
researcher_b 응답 코드: 200 200 200 200 200 429 429
$ sleep 30
$ 패널별 쿼리 결과 ($__range → 30m)
수집 대상 상태	4	[{"m":{},"v":1},{"m":{},"v":1},{"m":{},"v":1},{"m":{},"v":1}]
vLLM 대기열	1	[{"m":{},"v":0}]
vLLM 대기열	1	[{"m":{},"v":0}]
게이트웨이 진행 중 요청	1	[{"m":{},"v":0}]
게이트웨이 요청률(상태 코드별)	3	[{"m":{"status":"200"},"v":0.111},{"m":{"status":"401"},"v":0},{"m":{"status":"429"},"v":0}]
게이트웨이 지연 p50/p95	1	[{"m":{},"v":0.182}]
게이트웨이 지연 p50/p95	1	[{"m":{},"v":0.416}]
vLLM 첫 토큰 지연 p95	1	[{"m":{},"v":0.028}]
vLLM 전체 지연 p95	1	[{"m":{},"v":0.285}]
생성 처리량	1	[{"m":{},"v":0.889}]
사용자별 요청 수	4	[{"m":{"user":"admin"},"v":11.222},{"m":{"user":"researcher_a"},"v":11.222},{"m":{"user":"researcher_b"},"v":6.121},{"m":{"user":"unknown"},"v":0}]
사용자별 토큰	3	[{"m":{"user":"admin"},"v":529.489},{"m":{"user":"researcher_a"},"v":529.489},{"m":{"user":"researcher_b"},"v":136.708}]
사용자별 429	1	[{"m":{"user":"researcher_b"},"v":0}]
PII 마스킹 건수(종류별)	1	[{"m":{"kind":"phone"},"v":20.405}]
GPU 사용률	1	[{"m":{},"v":4}]
GPU 메모리	1	[{"m":{},"v":28.718}]
GPU 메모리	1	[{"m":{},"v":31.843}]
GPU 온도·전력	1	[{"m":{},"v":40}]
GPU 온도·전력	1	[{"m":{},"v":61.99}]
KV 캐시 사용률	1	[{"m":{},"v":0}]

$ Q 'gateway_requests_total{status="429"}'
[{"m":{"user":"researcher_b","status":"429"},"v":"2"}]
$ Q 'count_over_time(gateway_requests_total{status="429"}[30m])'
[{"m":{"user":"researcher_b","status":"429"},"v":"4"}]
$ Q 'min_over_time(gateway_requests_total{status="429"}[30m])'
[{"m":{"user":"researcher_b","status":"429"},"v":"2"}]
$ Q 'gateway_requests_total{status="401"}'
[{"m":{"user":"unknown","status":"401"},"v":"1"}]
$ Q 'increase(gateway_requests_total{status="401"}[30m])'
[{"m":{"user":"unknown","status":"401"},"v":"0"}]
```
