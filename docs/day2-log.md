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

## 3단계 PII 마스킹

규칙 (적용 순서: rrn → phone → mrn → email)

| 종류 | 패턴 요약 | 자리표시자 | 한계 |
|---|---|---|---|
| rrn (주민·외국인등록번호) | 생년월일 6자리(월 01~12, 일 01~31) + 하이픈 선택 + [1-8] + 6자리 | [주민번호] | 하이픈 대신 공백·점을 쓴 번호는 못 가린다. 2월 30일 같은 없는 날짜도 가린다 |
| phone | 휴대 01[016789]-?\d{3,4}-?\d{4}, 유선 (02\|0[3-6][1-5])-?\d{3,4}-?\d{4} | [전화번호] | 공백·점 구분, 국가번호(+82)는 못 가린다. 0으로 시작하는 10~11자리 숫자는 오탐 가능 |
| mrn (환자번호) | (환자번호\|등록번호\|MRN) + 선택 공백·콜론(: ：) + 숫자 6~10자리. 키워드는 남긴다 | [환자번호] | 키워드 없는 환자번호, 키워드와 숫자 사이에 다른 단어가 있으면 못 가린다 |
| email | 로컬부@도메인.최상위(영문 2자 이상) | [이메일] | 한글 도메인, 난독화(at, dot)는 못 가린다 |

공통 한계
- 숫자 경계는 \b 대신 (?<!\d), (?!\d)를 쓴다. 한글이 바로 붙어도 맞는다.
- messages의 content(문자열, type "text" 항목)만 가린다. tools, 함수 인자, 다른 필드는 가리지 않는다.
- 응답(모델 출력)은 가리지 않는다.
- 이름, 주소, 진단명 같은 자유 서술 PII는 정규식으로 잡지 않는다.

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| ruff | 오류 0건 | All checks passed | 통과 |
| pytest | 전부 통과 (기존 16 + 새) | 38 passed (새 22: 마스킹 19, proxy 3) | 통과 |
| 가려야 함 | 12개 모두 가림 | 12/12 | 통과 |
| 가리면 안 됨 | 5개 모두 그대로 | 5/5 | 통과 |
| 건수 검사 | rrn 1, phone 1, mrn 1, 총 3 | rrn 1, phone 1, mrn 1, email 0, 총 3 | 통과 |
| 실제 X-PII-Masked | 3 | 3 | 통과 |
| 모델 답 | 자리표시자가 보임 | "주민번호 [주민번호], 전화 [전화번호], 환자번호: [환자번호]" | 통과 |
| 응답 원본 번호 | 0건 | 0 | 통과 |
| 게이트웨이 로그 원본 번호 | 0건 | 0 (종료 후 다시 검색해도 0) | 통과 |

구성
- app/masking.py: mask_text(), mask_messages()(deepcopy 후 가림, 원본 불변). 건수는 rrn/phone/mrn/email 4개 키로 돌려준다.
- app/config.py: pii_masking: bool = True (GATEWAY_PII_MASKING).
- app/main.py: chat 요청의 messages를 가린 뒤 중계한다. request.state.pii_counts에 종류별 건수를 둔다.
  미들웨어가 /v1/chat/completions 응답 헤더 X-PII-Masked에 총 건수를 넣는다. 401·400·429에도 넣는다(가리기 전이면 0).
- 테스트에 쓴 번호는 모두 가짜다.

### 원본 출력

```text
$ uv run ruff check .
All checks passed!
(exit=0)

$ uv run pytest -q
......................................                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /home/beck/바탕화면/asan/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
38 passed, 1 warning in 0.30s
(exit=0)

$ uv run uvicorn app.main:app --host 127.0.0.1 --port 18080 (PID 141117)
$ curl -s -D /tmp/h.txt -o /tmp/b.json .../v1/chat/completions (researcher_a 키, "다음 문장을 한 글자도 바꾸지 말고 그대로 따라 써줘: 주민번호 900101-1234567, 전화 010-1234-5678, 환자번호: 12345678 /no_think", max_tokens 96)
HTTP 200 / 0.377997s
$ grep -i '^x-pii-masked' /tmp/h.txt
x-pii-masked: 3
$ jq -r '.choices[0].message.content' /tmp/b.json
주민번호 [주민번호], 전화 [전화번호], 환자번호: [환자번호]
$ grep -cE '900101|1234-5678|12345678' /tmp/b.json || true
0
$ grep -cE '900101|1234-5678|12345678' /tmp/gw.log || true
0

$ cat /tmp/gw.log
INFO:     Started server process [141121]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:18080 (Press CTRL+C to quit)
INFO:     127.0.0.1:37580 - "POST /v1/chat/completions HTTP/1.1" 200 OK
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [141121]
```

## 4단계 감사 로그

3단계 확인(이 단계 시작 시 판정 표에서 읽음): X-PII-Masked 3, 응답·로그 원본 번호 0/0, pytest 38/38. 모두 통과.

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| ruff | 오류 0건 | All checks passed | 통과 |
| pytest | 전부 통과 (기존 38 + 새 7) | 45 passed | 통과 |
| 로그 줄 수 | 약 10줄 | 10줄 (admin 1, researcher_a 1, researcher_b 7, 키 없음 1) | 통과 |
| researcher_b 429 | 1줄 이상, request_id 있음 | 2줄, request_id c1debc10…, f1ad339a…, error_type throttling_error | 통과 |
| 키 없음 | status 401, user_id null | 401, null | 통과 |
| 파일 권한 | 600 | 600 | 통과 |
| 폴더 권한 | 700 | 700 | 통과 |
| 키 원문 유출 | 0 | 0 / 0 / 0 | 통과 |
| 키 해시 유출 | 0 | 0 / 0 / 0 | 통과 |
| 본문·전화번호·Bearer 유출 | 0 | 0 | 통과 |
| 쓰기 실패 시 요청 | 200 유지 | 200, stderr "audit write failed: FileExistsError"만 출력 | 통과 |

구성
- app/audit.py: logger "gateway.audit"(propagate=False), RotatingFileHandler 10MB × 5. 파일을 열 때마다 600, 폴더를 만들 때 700.
  prompt_sha256()은 정규화 JSON(sort_keys, ensure_ascii=False, 구분자 최소)의 sha256. write_audit()은 예외를 삼키고 예외 이름만 stderr에 쓴다.
- app/main.py: 미들웨어가 /v1/* 응답마다 1줄을 쓴다(/healthz 제외). 처리되지 않은 예외도 status 500으로 1줄 남긴다.
  request.state에 identity, model, usage, prompt_sha256, error_type을 둔다. 해시는 마스킹 후 messages 기준이다.
- app/config.py: audit_log_path, audit_log_max_bytes, audit_log_backup_count.
- docs/security.md: 접근권한, 비밀정보, 로그, 알려진 한계.

메모
- user_id·key_alias는 식별 실패 시 "unknown" 대신 null로 기록한다(request.state.identity 기준).
- 다른 테스트 파일도 기본 경로(logs/audit.jsonl)에 쓰므로, pytest는 GATEWAY_AUDIT_LOG_PATH를 저장소 밖으로 지정해 돌렸다.
- 보존 90일은 가정이다. 자동 삭제는 아직 없다.

### 원본 출력

```text
$ uv run ruff check .
All checks passed!
(exit=0)

$ uv run pytest -q
.............................................                            [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /home/beck/바탕화면/asan/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
45 passed, 1 warning in 0.34s
(exit=0)

$ uv run uvicorn app.main:app --host 127.0.0.1 --port 18080 (PID 160383)
admin -> 200
researcher_a -> 200
$ sleep 61
researcher_b 1 -> 200
researcher_b 2 -> 200
researcher_b 3 -> 200
researcher_b 4 -> 200
researcher_b 5 -> 200
researcher_b 6 -> 429
researcher_b 7 -> 429
키 없음 -> 401

$ wc -l logs/audit.jsonl
10 logs/audit.jsonl
$ stat -c '%a' logs/audit.jsonl logs
600
700
$ jq -r '[.user_id, .status] | @tsv' logs/audit.jsonl | sort | uniq -c
      1 	401
      1 admin	200
      1 researcher_a	200
      5 researcher_b	200
      2 researcher_b	429
$ jq -c 'select(.status==429) | {ts, request_id, user_id, key_alias, error_type}' logs/audit.jsonl
{"ts":"2026-11-24T06:22:21.502Z","request_id":"c1debc107a2f4580b78696e98ee291a1","user_id":"researcher_b","key_alias":"researcher_b","error_type":"throttling_error"}
{"ts":"2026-11-24T06:22:21.516Z","request_id":"f1ad339ab4564e3eab4dc87bb61d3a0c","user_id":"researcher_b","key_alias":"researcher_b","error_type":"throttling_error"}
$ jq -s 'group_by(.user_id) | map({user: .[0].user_id, req: length, tokens: (map(.total_tokens // 0) | add)})' logs/audit.jsonl
[{"user":null,"req":1,"tokens":0},{"user":"admin","req":1,"tokens":51},{"user":"researcher_a","req":1,"tokens":51},{"user":"researcher_b","req":7,"tokens":105}]
$ 유출 검사: 키 3개
0
0
0
$ grep -cE '010-1234-5678|연락 달라|Bearer' logs/audit.jsonl || true
0
$ 키 sha256 해시 검색 (3개)
0
0
0
```

## 5a단계 게이트웨이 Docker화

| 항목 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 이미지 크기 | 기록만 | 284MB (llm-gateway:day2, python:3.12-slim + uv 0.13.6) | 기록만 |
| 비root uid | 10001 | 10001 | 통과 |
| 이미지 안 .env 없음 | /app에 .env 없음 | .venv, app, logs, pyproject.toml, uv.lock만 있음. .env·*.key·.git·tests 없음 | 통과 |
| 로그 폴더 700 | drwx------ gateway | drwx------ gateway gateway. 로그 파일 600 gateway | 통과 |
| 18080 127.0.0.1만 | 127.0.0.1:18080 | 127.0.0.1:18080 LISTEN | 통과 |
| healthy | 3분 이내 | 약 30초 (15:28:13 starting → 15:28:43 healthy) | 통과 |
| whoami 3/3 | admin, researcher_a, researcher_b | 3/3 일치 | 통과 |
| PII 헤더 | x-pii-masked: 1 | x-pii-masked: 1, HTTP 200, 0.41 s | 통과 |
| 키 없음 401 | 401 | 401 | 통과 |
| 감사 로그 줄 수 | 5줄 | 5줄 (whoami 3, chat 1, models 401 1) | 통과 |
| 키 유출 0 | 0 | 0 / 0 / 0. 전화번호·Bearer도 0 | 통과 |
| pytest 통과 | 45/45, ruff 0건 | 45 passed, All checks passed | 통과 |

구성
- Dockerfile: python:3.12-slim + uv 0.13.6, uv sync --frozen --no-dev --no-install-project, 비root gateway(uid 10001), HEALTHCHECK /healthz.
- .dockerignore: .env·키·.git·logs·tests·docs 등을 빌드 컨텍스트에서 뺀다(컨텍스트 110.74kB).
- compose.yaml: gateway 서비스(127.0.0.1:18080→8080, backend 망, http://litellm:4000)와 auditlogs 볼륨만 추가했다. 기존 서비스 정의는 그대로다.
- tests/conftest.py: 모든 테스트의 감사 로그를 tmp_path로 보낸다. 실행 후 저장소 logs/audit.jsonl 크기·수정 시각이 그대로인 것을 확인했다.
- vllm, litellm, litellm-db는 재시작하지 않았다(StartedAt 전후 동일).

메모
- 이미지 안에 /app/app/__pycache__가 들어갔다. .dockerignore의 `__pycache__/`는 컨텍스트 최상위에만 맞는다. 하위 폴더까지 빼려면 `**/__pycache__`가 필요하다.
- 컨테이너 감사 로그의 client_ip가 172.19.0.1(Docker 브리지)로 기록된다. 호스트 포트 포워딩을 거치면 실제 요청자 IP가 보이지 않는다.

### 원본 출력

```text
$ docker image ls llm-gateway:day2 --format '{{.Size}}'
284MB

$ docker compose up -d --no-deps gateway
 Volume llm-platform_auditlogs Creating 
 Volume llm-platform_auditlogs Creating 
 Volume llm-platform_auditlogs Created 
 Volume llm-platform_auditlogs Created 
 Container llm-gateway Creating 
 Container llm-gateway Created 
 Container llm-gateway Starting 
 Container llm-gateway Started 
(exit=0)
[15:28:13] Up Less than a second (health: starting)
[15:28:43] Up 30 seconds (healthy)

$ docker compose exec gateway id -u
10001
(exit=0)

$ docker compose exec gateway ls -a /app
.
..
.venv
app
logs
pyproject.toml
uv.lock
(exit=0)

$ docker compose exec gateway sh -c 'ls -ld /app/logs'
drwx------ 2 gateway gateway 4096 Nov 24 06:28 /app/logs
(exit=0)

$ ss -tlnH | grep ':18080 '
LISTEN 0      4096       127.0.0.1:18080 0.0.0.0:*
(exit=0)

$ docker compose ps --format '{{.Name}}\t{{.Status}}'
litellm	Up 3 hours
litellm-db	Up 3 hours (healthy)
llm-gateway	Up 37 seconds (healthy)
vllm	Up 2 hours (healthy)
(exit=0)

$ for u in admin researcher_a researcher_b; do curl .../v1/whoami | jq -c {user_id}; done
{"user_id":"admin"}
{"user_id":"researcher_a"}
{"user_id":"researcher_b"}

$ curl -s -D /tmp/h.txt -o /tmp/b.json .../v1/chat/completions (researcher_a 키, "전화 010-1234-5678 문장을 한 줄로 요약해줘. /no_think", max_tokens 48)
time_total=0.409181s
$ grep -iE '^(HTTP|x-request-id|x-pii-masked)' /tmp/h.txt; jq -r '.choices[0].message.content' /tmp/b.json
HTTP/1.1 200 OK
x-request-id: 87055ea5b9984c88b5e4a1cf294ba6ea
x-pii-masked: 1
전화번호로 문장을 한 줄로 요약하면 다음과 같습니다:

"전화번호를 통해 문장을 전달합니다."

키 없음 -> 401

$ docker compose exec gateway sh -c 'wc -l /app/logs/audit.jsonl; tail -1 /app/logs/audit.jsonl' | head -c 1200
5 /app/logs/audit.jsonl
{"ts": "2026-11-24T06:29:06.565Z", "request_id": "cf3a0f4b3849427095d49fca2456ef2e", "user_id": null, "key_alias": null, "method": "GET", "path": "/v1/models", "status": 401, "latency_ms": 0, "model": null, "prompt_tokens": null, "completion_tokens": null, "total_tokens": null, "pii_counts": {}, "pii_total": 0, "prompt_sha256": null, "error_type": "missing_api_key", "client_ip": "172.19.0.1"}

$ 키 3개 grep -cF (0이면 종료 코드 1)
0
0
0
$ docker compose exec gateway sh -c 'stat -c "%a %U" /app/logs/audit.jsonl'
600 gateway
$ grep -cE '010-1234-5678|Bearer' (컨테이너 감사 로그)
0

$ uv run ruff check .
All checks passed!
(exit=0)
$ uv run pytest -q
45 passed, 1 warning in 0.31s
(exit=0)
```
