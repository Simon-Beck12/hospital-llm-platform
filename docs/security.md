# 보안 설계

사내 LLM 서빙 플랫폼(vLLM + LiteLLM + FastAPI 게이트웨이)의 접근권한, 비밀정보, 로그, 알려진 한계를 정리한다.

## 접근권한

| 계정 | 그룹 | sudo | docker | 용도 |
|---|---|---|---|---|
| beck | llm-admins | 있음 | 있음 | 서버 소유자 |
| admin | llm-admins | 있음 | 있음 | 운영 관리자 |
| researcher_a | llm-users | 없음 | 없음 | 연구자 |
| researcher_b | llm-users | 없음 | 없음 | 연구자 |

- SSH는 키 인증만 허용한다. PasswordAuthentication no, KbdInteractiveAuthentication no, PermitRootLogin no, MaxAuthTries 3.
- AllowGroups llm-admins llm-users. 두 그룹 밖 계정은 SSH로 들어올 수 없다.
- docker 그룹은 관리자만 둔다. docker 그룹은 사실상 root 권한이라 연구자는 docker.sock에 접근하지 못한다(permission denied 확인).
- 홈 디렉터리는 750. 모델 폴더 /srv/models는 beck:llm-admins, 2775.

## 비밀정보

- `.env`(LiteLLM 마스터 키, salt 키, Postgres 비밀번호)는 권한 600이고 Git에서 제외한다. `.env.example`에는 빈 값만 둔다.
- 게이트웨이는 마스터 키를 갖지 않는다. 요청자 본인 키를 LiteLLM에 그대로 넘기고, 계정 식별도 본인 키로 `/key/info`를 부른다.
- 마스터 키를 쓰는 곳은 LiteLLM 컨테이너와 키 발급 스크립트(`scripts/issue_keys.sh`)뿐이다.
- 발급한 키는 `~/llm-keys/<계정>.key`(폴더 700, 파일 600)에 둔다. 연구자 홈에는 `~/.llm_key`(소유자 본인, 600)로 배치한다.
- LiteLLM은 127.0.0.1:4000에만 열고, vLLM과 Postgres는 호스트 포트를 열지 않는다.
- scripts/check_secrets.sh(gitleaks v8.30.1)로 Git 이력을 검사한다. 커밋 전에 실행한다. 확인된 오탐은 `.gitleaksignore`에 지문과 이유를 적는다.

## 로그

게이트웨이는 `/v1/*` 요청마다 감사 로그를 JSON 한 줄로 남긴다(`logs/audit.jsonl`, 폴더 700, 파일 600).

| 필드 | 내용 |
|---|---|
| ts | UTC ISO8601, 밀리초, Z |
| request_id | X-Request-ID(검증 통과 값 또는 새 uuid4 hex) |
| user_id, key_alias | 키로 식별한 계정. 실패하면 null |
| method, path, status, latency_ms | 요청 메서드, 경로, 응답 코드, 처리 시간(ms, 정수) |
| model | 요청한 모델 이름 |
| prompt_tokens, completion_tokens, total_tokens | 응답 usage. 없으면 null |
| pii_counts, pii_total | 종류별·전체 마스킹 건수 |
| prompt_sha256 | 마스킹 후 messages의 sha256(chat만) |
| error_type | 오류 응답의 error.type(예: missing_api_key, throttling_error) |
| client_ip | 요청자 IP |

- 프롬프트·응답 본문, Authorization 헤더, API 키 원문과 키 해시는 남기지 않는다. 본문 대신 마스킹 후 해시만 남긴다.
- 10MB × 5개로 회전한다(최대 약 60MB).
- 보존 기간은 90일로 가정한다(포트폴리오 가정, 자동 삭제는 아직 없음).
- 로그 쓰기에 실패해도 요청은 실패시키지 않는다. 표준 에러에 예외 이름만 출력한다.
- 한도 초과 조회 예: `jq -c 'select(.status==429) | {ts, request_id, user_id}' logs/audit.jsonl`

## 알려진 한계

- 키를 폐기해도 게이트웨이 식별 캐시 때문에 최대 300초 동안 예전 user_id로 기록될 수 있다. 실제 요청 차단은 LiteLLM이 한다.
- 모델 응답은 마스킹하지 않는다.
- 키워드(환자번호/등록번호/MRN) 없는 환자번호, 공백·점으로 구분한 번호, +82 전화번호는 못 가린다.
- 이름, 주소, 진단명 같은 자유 서술 개인정보는 정규식으로 잡지 않는다.
- 클라이언트 IP는 게이트웨이 앞에 프록시가 생기면 프록시 IP로 기록된다.
- 컨테이너 감사 로그의 client_ip는 Docker 브리지 주소(예: 172.19.0.1)다. 실제 요청자 IP는 앞단 프록시의 X-Forwarded-For가 필요하다.
