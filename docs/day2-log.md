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
