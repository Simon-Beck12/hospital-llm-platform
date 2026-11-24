# 게이트웨이 API 오류와 추적

컨테이너 게이트웨이(127.0.0.1:18080)에서 2026-11-24에 재현한 오류 5종이다. 모든 응답에는 `x-request-id` 헤더가 붙고, 같은 값이 감사 로그(`/app/logs/audit.jsonl`, auditlogs 볼륨)의 `request_id`에 남는다.

## 오류 표

| 코드 | 재현 방법 | 응답 error.type | 누가 만든 오류 | 요청 ID 예시 | 추적 경로 | 조치 |
|---|---|---|---|---|---|---|
| 401a | Authorization 헤더 없이 `GET /v1/models` | missing_api_key | 게이트웨이 | aa079d77e2504eb6880a5bf13288138f | 감사 로그만(업스트림 호출 없음). user_id null, latency 0 ms | `Authorization: Bearer <발급 키>` 헤더를 붙인다 |
| 401b | `Authorization: Bearer sk-wrong`(가짜 키)로 `GET /v1/models` | token_not_found_in_db | LiteLLM | b79f499f0f0f48a3be0b0cc14bec5f6d | 감사 로그(user_id null, 28 ms) → LiteLLM 로그 "Invalid proxy server token passed ... not found in db" | 키 오타·만료 확인. 필요하면 admin이 재발급 |
| 429 | researcher_b 키(rpm 5)로 1분 안에 chat 7회 | throttling_error (Retry-After: 60) | LiteLLM | 4cc2d8cf93db4ebc9f23eb8a658d5be7 | 감사 로그(user_id researcher_b, 6 ms) → LiteLLM 접근 로그 429 | Retry-After 초만큼 기다린 뒤 재시도. 한도 상향은 admin 결정 |
| 502 | `docker compose stop litellm` 뒤 chat 요청 | upstream_unavailable | 게이트웨이 | 79cb868ccbf0481eabb5eed3cb572972 | 감사 로그(user_id null, 4 ms) → `docker compose ps litellm`, LiteLLM 로그(멈춘 동안 기록 없음, 재기동 로그) | litellm 컨테이너 상태 확인 후 `docker compose start litellm`. 복구 20초 |
| 504 | 타임아웃 0.5초 임시 게이트웨이(18081)로 max_tokens 512 chat 요청 | upstream_timeout | 게이트웨이 | 7e066202fd4d47a18bbdab580556abd5 | 감사 로그(user_id researcher_a, 518 ms) → LiteLLM 로그(/key/info 200만 있고 chat 줄 없음) → vLLM 로그(chat 200) | GATEWAY_UPSTREAM_TIMEOUT_S(기본 60초)와 max_tokens 조정. 타임아웃 후에도 vLLM은 생성을 끝까지 계속함(GPU 점유) |

측정값
- 502 복구 소요: litellm 재시작 후 20초(10초 간격 liveliness 확인, 멈춘 시각 15:34:55, 다시 켠 시각 15:34:56, 200 확인 15:35:16).
- 504 응답 시간: 0.54초(curl time_total), 감사 로그 latency_ms 518.
- 502는 researcher_a가 식별 캐시에 없어서 식별 단계도 실패했다(user_id null). 식별 실패는 요청을 막지 않으므로 중계 단계에서 502가 났다.

## 추적 순서

1. 응답 헤더 `x-request-id`를 확인한다. 오류 본문의 `error.request_id`도 같은 값이다(게이트웨이가 만든 오류).
2. 감사 로그에서 request_id로 찾는다.
   `docker compose exec gateway grep -F '<request_id>' /app/logs/audit.jsonl`
3. `status`, `error_type`, `user_id`, `latency_ms`를 확인한다. error_type으로 게이트웨이 오류(missing_api_key, upstream_unavailable, upstream_timeout)와 LiteLLM 오류(token_not_found_in_db, throttling_error)를 나눈다.
4. 502·504는 LiteLLM 로그를 본다.
   `docker compose logs --since 10m litellm | grep -iE 'error|timeout|disconnect' | tail -5`
   LiteLLM 로그에는 요청 ID가 없다. 감사 로그의 `ts`와 게이트웨이 컨테이너 IP(예: 172.19.0.5)로 맞춘다.

## 참고

- 감사 로그 조회 예: `docker compose exec gateway sh -c "grep '\"status\": 429' /app/logs/audit.jsonl"`
- 504 재현에 쓴 임시 컨테이너(gw-timeout-test)는 볼륨 없이 띄웠다. 그 감사 로그는 컨테이너와 함께 지워졌고, 위 값은 재현 직후 출력에서 옮겼다.
