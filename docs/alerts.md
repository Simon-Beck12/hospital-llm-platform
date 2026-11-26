# 알림 규칙

Prometheus 알림 규칙은 [monitoring/alerts.yml](../monitoring/alerts.yml)에 있다(그룹 `llm-platform`). [monitoring/prometheus.yml](../monitoring/prometheus.yml)의 `rule_files`가 이 파일을 읽는다. 컨테이너 안의 경로는 `/etc/prometheus/alerts.yml`이다. 규칙 평가 간격은 15초, 수집 간격도 15초다.

## 규칙

| 이름 | 조건 | 지속 | 심각도 | 대응 문서 |
|---|---|---|---|---|
| VLLMDown | `up{job="vllm"} == 0` | 1분 | critical | [INC-001](incidents/INC-001-vllm-crash.md) |
| GatewayDown | `up{job="gateway"} == 0` | 1분 | critical | [장애 목록](incidents/README.md) |
| GPUHighTemperature | `nvidia_smi_temperature_gpu > 85` (℃) | 2분 | warning | [부하 테스트](loadtest.md) |
| KVCacheHigh | `vllm:kv_cache_usage_perc > 0.9` (비율 0~1) | 5분 | warning | [부하 테스트](loadtest.md) |

- 각 규칙에는 `annotations.summary`(한국어 1줄)와 `annotations.runbook`(대응 문서 경로)이 있다.
- 임계값의 근거는 3일차 부하 테스트(동시 사용자 32명)에서 측정한 최대값이다. 온도는 최대 75℃, KV 캐시는 최대 3.01%였다. 평소 부하에서는 울리지 않는 값으로 정했다.
- 조건이 처음 참이 되면 pending이 되고, 지속 시간 동안 계속 참이면 firing이 된다. 조건이 거짓이 되면 다음 평가(최대 15초 뒤)에 해제된다.
- VLLMDown 실측(2026-11-26): vLLM을 멈춘 뒤 pending까지 25초, firing까지 85초 걸렸다. 다시 켠 뒤 up=1이 되고 약 13초 뒤 해제됐다. 증거는 [alert-vllmdown.txt](../evidence/day4/alert-vllmdown.txt)에 있다.

## Alertmanager를 넣지 않은 이유

- 폐쇄망 환경이고, 아직 알림을 보낼 곳(사내 메일 서버, 메신저 웹훅)이 정해지지 않았다. 그래서 지금은 Prometheus가 알림 상태만 계산하고, 화면과 API로 확인한다.
- 나중에 확장할 때는 Alertmanager를 추가하고 사내 메일(SMTP)이나 메신저 웹훅으로 연동한다. 그때 규칙 파일은 그대로 쓴다.

## 확인 방법

- 브라우저: http://127.0.0.1:9090/alerts (규칙별 inactive, pending, firing 상태)
- API:

```bash
# 규칙 4개의 상태(health는 ok여야 함)
curl -s 127.0.0.1:9090/api/v1/rules | jq '[.data.groups[].rules[] | {name, health, state}]'
# 지금 활성 상태(pending 또는 firing)인 알림
curl -s 127.0.0.1:9090/api/v1/alerts | jq -c '[.data.alerts[] | {name:.labels.alertname, state, activeAt}]'
# 지난 알림 기록(ALERTS 시계열)
curl -s 127.0.0.1:9090/api/v1/query --data-urlencode 'query=ALERTS'
```

- 규칙 문법 검사:

```bash
docker run --rm -v "$PWD/monitoring:/m:ro" --entrypoint promtool prom/prometheus:v3.15.1 check rules /m/alerts.yml
```
