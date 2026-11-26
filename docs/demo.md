# 시연 순서

[scripts/demo.sh](../scripts/demo.sh)로 장면 7개를 순서대로 보여 준다. 장면마다 제목과 설명 1줄이 먼저 나오고, Enter를 누르면 다음 장면으로 넘어간다(`DEMO_AUTO=1`이면 멈추지 않음). 예행 출력은 [demo-dryrun.txt](../evidence/day4/demo-dryrun.txt)에 있다.

| 순서 | 보여 주는 것 | 명령 또는 화면 | 연결되는 자격 |
|---|---|---|---|
| 1 | 스택 상태: 7개 서비스, healthy 3개 | `docker compose ps` | Docker 배포·운영 |
| 2 | 계정 식별: 본인 키로 계정 확인(마스터 키 없음) | `GET /v1/whoami` (researcher_a) | REST API 연동, 접근권한 관리 |
| 3 | PII 마스킹: 가짜 주민번호·전화번호 가림, 헤더 `x-pii-masked: 2` | `POST /v1/chat/completions` (researcher_a) | 백엔드 FastAPI, 비밀정보·로그 관리 |
| 4 | 사용량 한도: 분당 5회 한도에서 6회째부터 429, `Retry-After: 60` | chat 7회 연속 (researcher_b) | REST API 디버깅, 접근권한 관리 |
| 5 | 감사 로그: 본문 없이 `prompt_sha256`, 사용자, 상태, PII 건수만 기록 | `docker exec llm-gateway tail -n 3 /app/logs/audit.jsonl` | 로그 관리, Linux 운영 |
| 6 | 알림 규칙 4개: 상태와 health ok | `GET 127.0.0.1:9090/api/v1/rules` | Linux 운영·장애 분석 |
| 7 | Grafana 대시보드: 요청률, 지연, 사용자별 429, GPU | 브라우저 http://127.0.0.1:3000/d/llm-platform | Docker 운영, 장애 분석 |

- 장면 3의 응답에서 이름(가짜 "홍길동")은 가려지지 않는다. 이름 같은 자유 서술 개인정보는 정규식으로 잡지 않는다는 알려진 한계다([security.md](security.md)). 시연할 때 함께 설명한다.

## 녹화 전 준비

1. 브라우저는 F11 전체 화면으로 북마크 바, 주소창, 탭을 숨긴다.
2. 터미널 글자 크기를 키운다(예: Ctrl+Shift+= 2~3회). 키 값이나 `.env`가 화면에 나오는 창은 닫는다.
3. researcher_b의 분당 한도를 비우기 위해 직전 요청 후 61초를 쉬고 `./scripts/demo.sh`를 시작한다.

- 녹화한 영상은 저장소에 넣지 않는다(용량, 화면에 개인정보가 찍힐 위험).
