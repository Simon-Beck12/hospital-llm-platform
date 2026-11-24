# 2일차 작업 기록

날짜: 2026-11-24

## 1단계 게이트웨이 골격

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| v0.1-day1 태그 | origin에 있음 | refs/tags/v0.1-day1 → 9ce7638 (main) | 통과 |
| 게이트웨이 포트 | 8080 비면 8080, 아니면 18080 | 8080은 frappe 사용 중 → 18080 | 통과 |
| ruff | 오류 0건 | All checks passed | 통과 |
| pytest | 8개 통과 (기존 1 + 새 7) | 8 passed, 경고 1건 | 통과 |
| 인증 없음 | 401, 업스트림 호출 없음 | 401 | 통과 |
| 게이트웨이 경유 응답 | 200, x-request-id: day2-test-001, 한국어 답 | 200, x-request-id: day2-test-001, "안녕하세요! 😊", 0.17 s | 통과 |
| 잘못된 키 | 401 (LiteLLM이 거절) | 401 | 통과 |

구성
- app/config.py: GATEWAY_ 접두사 설정(litellm_base_url, upstream_timeout_s), lru_cache로 한 번만 만든다.
- app/proxy.py: lifespan에서 httpx.AsyncClient 하나를 만들고 닫는다. forward()는 Authorization, X-Request-ID, Content-Type만 보낸다.
  TimeoutException → 504 upstream_timeout, 연결 오류 → 502 upstream_unavailable, JSON 아님 → 502 upstream_bad_response.
- app/main.py: X-Request-ID 미들웨어, Bearer 검사(401 missing_api_key), GET /v1/models, POST /v1/chat/completions.
  본문이 JSON 객체가 아니면 400 invalid_request, stream: true면 400 stream_not_supported. 업스트림 상태 코드는 그대로 돌려준다.
- tests/test_proxy.py: httpx.MockTransport로 업스트림을 흉내 낸 테스트 7개.

메모
- 502 처리는 ConnectError만이 아니라 httpx.TransportError 전체(연결 끊김 등)로 넓혔다. 처리되지 않은 500을 줄이기 위해서다.
- 업스트림 응답 헤더(예: 429의 Retry-After)는 아직 전달하지 않는다.
- 응답 지연 측정을 위해 10단계 curl에 -w time_total을 더했다.

### 원본 출력

```text
$ uv run ruff check .
All checks passed!
(exit=0)

$ uv run pytest -q
........                                                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /home/beck/바탕화면/asan/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
8 passed, 1 warning in 0.27s
(exit=0)

$ uv run uvicorn app.main:app --host 127.0.0.1 --port 18080 (PID 108671)
$ curl -X POST .../v1/chat/completions (Authorization 없음)
인증 없음 -> 401

$ curl -s -D - -o /tmp/gw_ok.json .../v1/chat/completions -H "Authorization: Bearer $(cat ~/llm-keys/researcher_a.key)" -H "X-Request-ID: day2-test-001" ("한 줄로 인사해줘. /no_think", max_tokens 32) | grep -iE "^HTTP|^x-request-id"
HTTP/1.1 200 OK
x-request-id: day2-test-001
time_total=0.165258s
$ jq -r '.choices[0].message.content' /tmp/gw_ok.json


안녕하세요! 😊

$ curl .../v1/models -H "Authorization: Bearer sk-wrong"
잘못된 키 -> 401

$ cat /tmp/gw.log
INFO:     Started server process [108675]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:18080 (Press CTRL+C to quit)
INFO:     127.0.0.1:52266 - "POST /v1/chat/completions HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:52270 - "POST /v1/chat/completions HTTP/1.1" 200 OK
INFO:     127.0.0.1:52286 - "GET /v1/models HTTP/1.1" 401 Unauthorized
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [108675]
```

## 2단계 사용자 식별

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| ruff | 오류 0건 | All checks passed | 통과 |
| pytest | 16개 통과 (기존 8 + 새 8) | 16 passed, 경고 1건 | 통과 |
| 캐시 적중 | 같은 키 2회 → /key/info 1회 | 1회 (test_same_key_hits_cache) | 통과 |
| 캐시 만료 | 301초 뒤 다시 호출 | 2회 (test_cache_expires_after_ttl) | 통과 |
| whoami admin | user_id admin | admin | 통과 |
| whoami researcher_a | user_id researcher_a | researcher_a | 통과 |
| whoami researcher_b | user_id researcher_b | researcher_b | 통과 |
| 잘못된 키 whoami | 401 | 401 | 통과 |
| 잘못된 X-Request-ID | 32자 hex로 교체 | "bad id!" → 475a2b09306849ad802afe5686f69065 | 통과 |
| researcher_b 429 | 요청 6~7 중 429 | 1~5 200, 6·7 429 | 통과 |
| Retry-After 전달 | 있으면 전달 (없으면 기록만) | retry-after: 60. x-ratelimit-* 4개도 전달 | 통과 |
| 응답 앞 빈 줄 제거 | content가 줄바꿈으로 시작하지 않음 | "Hello! How can" | 통과 |

구성
- app/identity.py: Identity, IdentityCache(TTL 300초, 최대 1000개, sha256 키, 시계 주입), resolve_identity().
  /key/info를 요청자 본인 키로 부른다. 200이 아니거나 연결 오류면 None을 돌려주고 캐시하지 않는다.
- app/main.py: X-Request-ID 검증(^[A-Za-z0-9._-]{1,64}$, 안 맞으면 새 uuid4 hex), identify 의존성(request.state.user_id/key_alias, 실패 시 "unknown"),
  GET /v1/whoami(실패 시 401 unknown_api_key), chat 200 응답의 content 앞 공백 lstrip.
- app/proxy.py: forward()가 Retry-After와 x-ratelimit-* 헤더를 함께 돌려준다.

메모
- 게이트웨이 코드는 마스터 키를 읽지 않는다. 사전 확인에서 본인 키로 /key/info가 3개 모두 200이었다.
- 식별 실패는 요청을 막지 않는다. 키 검증은 LiteLLM이 한다.
- 429 메시지의 api_key 해시는 이 기록에서 가렸다.
- 게이트웨이 경유 지연: 200은 0.11~0.13 s, 429는 0.007 s.

### 원본 출력

```text
$ uv run ruff check .
All checks passed!
(exit=0)

$ uv run pytest -q
................                                                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /home/beck/바탕화면/asan/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
16 passed, 1 warning in 0.28s
(exit=0)

$ uv run uvicorn app.main:app --host 127.0.0.1 --port 18080 (PID 117805)
$ for u in admin researcher_a researcher_b; do curl .../v1/whoami -H "Authorization: Bearer $(cat ~/llm-keys/$u.key)" | jq -c "{user_id, key_alias}"; done
{"user_id":"admin","key_alias":"admin"}
{"user_id":"researcher_a","key_alias":"researcher_a"}
{"user_id":"researcher_b","key_alias":"researcher_b"}
잘못된 키 whoami -> 401

$ curl -s -D - -o /dev/null .../v1/models -H "Authorization: Bearer $(cat ~/llm-keys/researcher_a.key)" -H "X-Request-ID: bad id!" | grep -i "^x-request-id"
x-request-id: 475a2b09306849ad802afe5686f69065

$ sleep 61
$ for i in 1..7: researcher_b 키로 POST .../v1/chat/completions ("hi /no_think", max_tokens 8)
13:58:38 요청 1 -> 200 (0.129778s)
13:58:38 요청 2 -> 200 (0.109691s)
13:58:39 요청 3 -> 200 (0.109761s)
13:58:39 요청 4 -> 200 (0.109334s)
13:58:39 요청 5 -> 200 (0.109513s)
13:58:39 요청 6 -> 429 (0.006688s)
13:58:39 요청 7 -> 429 (0.006605s)
$ grep -iE '^(retry-after|x-ratelimit)' /tmp/h_7.txt || echo '429 응답에 Retry-After 없음'
retry-after: 60
$ jq -r '.choices[0].message.content | @json' /tmp/b_1.json
"Hello! How can"
$ jq -c '.error | {type, message}' /tmp/b_7.json (해시 가림)
{"type":"throttling_error","code":"429","message":"Rate limit exceeded for api_key: <해시 가림>. Limit type: requests. Current limit: 5, Remaining: 0. Limit resets at: 2026-11-24 04:59:39 UTC"}

$ cat /tmp/gw.log
INFO:     Started server process [117809]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:18080 (Press CTRL+C to quit)
INFO:     127.0.0.1:47810 - "GET /v1/whoami HTTP/1.1" 200 OK
INFO:     127.0.0.1:47826 - "GET /v1/whoami HTTP/1.1" 200 OK
INFO:     127.0.0.1:47834 - "GET /v1/whoami HTTP/1.1" 200 OK
INFO:     127.0.0.1:47844 - "GET /v1/whoami HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:47858 - "GET /v1/models HTTP/1.1" 200 OK
INFO:     127.0.0.1:49610 - "POST /v1/chat/completions HTTP/1.1" 200 OK
INFO:     127.0.0.1:49618 - "POST /v1/chat/completions HTTP/1.1" 200 OK
INFO:     127.0.0.1:49620 - "POST /v1/chat/completions HTTP/1.1" 200 OK
INFO:     127.0.0.1:49630 - "POST /v1/chat/completions HTTP/1.1" 200 OK
INFO:     127.0.0.1:49634 - "POST /v1/chat/completions HTTP/1.1" 200 OK
INFO:     127.0.0.1:49642 - "POST /v1/chat/completions HTTP/1.1" 429 Too Many Requests
INFO:     127.0.0.1:49656 - "POST /v1/chat/completions HTTP/1.1" 429 Too Many Requests
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [117809]
```
