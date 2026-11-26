# 문서 목차

저장소 소개와 핵심 숫자는 [../README.md](../README.md)에 있다.

## 설계·정책

| 파일 | 설명 |
|---|---|
| [security.md](security.md) | 접근권한(계정·그룹·SSH), 비밀정보, 감사 로그 필드, 알려진 한계 |
| [quota-policy.md](quota-policy.md) | 3일차 실측 기반 역할별 RPM/TPM 한도, 수용 인원 계산, 키 수명, 실측 검증 |
| [api-errors.md](api-errors.md) | 게이트웨이 오류 5종(401×2, 429, 502, 504) 재현과 요청 ID 추적 순서 |
| [scale-out.md](scale-out.md) | 확장 설계안(용량 공식, 다중 GPU·노드, SSO, 비밀정보, 관측, 공급망, 백업). 미구현 |

## 운영

| 파일 | 설명 |
|---|---|
| [alerts.md](alerts.md) | Prometheus 알림 규칙 4개, Alertmanager를 넣지 않은 이유, 확인 방법, VLLMDown 실측 |
| [loadtest.md](loadtest.md) | Locust 부하 시험(동시 사용자 1/8/32명) 조건, 결과, 해석 |
| [offline.md](offline.md) | 폐쇄망 기동 시험 방법과 결과, 끈 텔레메트리, 반입 절차, 한계 |
| [backup.md](backup.md) | 백업 대상과 제외 이유, 보안, 복구 시험 실측, 운영 복구 절차, 주기 제안 |
| [incidents/README.md](incidents/README.md) | 장애 목록 |
| [incidents/INC-001-vllm-crash.md](incidents/INC-001-vllm-crash.md) | vLLM 컨테이너 강제 종료(중단 124초, 수동 복구) |
| [incidents/INC-002-gpu-memory.md](incidents/INC-002-gpu-memory.md) | GPU 메모리 부족으로 vLLM 기동 실패(중단 101초, 자동 재기동) |

## 작업 기록

| 파일 | 설명 |
|---|---|
| [day1-log.md](day1-log.md) | 1일차: 사전 점검, 계정과 모델, SSH 강화, Docker GPU 런타임, 기동, 계정별 키와 429 |
| [day2-log.md](day2-log.md) | 2일차: 게이트웨이 골격, 사용자 식별, PII 마스킹, 감사 로그, Docker화, 오류 재현 |
| [day3-log.md](day3-log.md) | 3일차: 게이트웨이 지표, Prometheus, Grafana, 부하 시험, 장애 재현 |
| [day4-log.md](day4-log.md) | 4일차: 알림 규칙, 한도·텔레메트리·폐쇄망, 백업·복구, README와 확장 설계안 |

## 증거 파일 (evidence/)

| 파일 | 설명 |
|---|---|
| [day1/429.png](../evidence/day1/429.png) | 한도 초과 429 응답 화면 |
| [day3/dashboard.png](../evidence/day3/dashboard.png) | Grafana 대시보드(최근 6시간) |
| [day3/dashboard-load.png](../evidence/day3/dashboard-load.png) | Grafana 대시보드(부하 시험 구간) |
| [day3/inc-001-timeline.txt](../evidence/day3/inc-001-timeline.txt) | INC-001 10초 간격 상태·HTTP 코드·up 값 |
| [day3/inc-001-logs.txt](../evidence/day3/inc-001-logs.txt) | INC-001 핵심 로그(docker events, vLLM, LiteLLM, 감사 로그) |
| [day3/inc-002-timeline.txt](../evidence/day3/inc-002-timeline.txt) | INC-002 상태·HTTP 코드·재시작 기록 |
| [day3/inc-002-logs.txt](../evidence/day3/inc-002-logs.txt) | INC-002 vLLM 메모리 부족 오류 줄 |
| [day3/inc-002-diagnosis.txt](../evidence/day3/inc-002-diagnosis.txt) | INC-002 nvidia-smi 프로세스 목록과 계산식 |
| [day4/alert-vllmdown.txt](../evidence/day4/alert-vllmdown.txt) | VLLMDown inactive → pending → firing → 해제 기록 |
| [day4/key-limits.txt](../evidence/day4/key-limits.txt) | 키 4개의 한도·만료 조회 결과(키 값 없음) |
| [day4/offline-check-online.txt](../evidence/day4/offline-check-online.txt) | 폐쇄망 시험 온라인 예행연습 출력 |
| [day4/offline-check-offline.txt](../evidence/day4/offline-check-offline.txt) | 폐쇄망 시험 오프라인 출력 |
| [day4/backup-run-attempt1.txt](../evidence/day4/backup-run-attempt1.txt) | 백업 첫 실행(tar 경고를 놓친 버전) 출력 |
| [day4/backup-run.txt](../evidence/day4/backup-run.txt) | 기준 백업 실행 출력과 manifest |
| [day4/backup-key-check.txt](../evidence/day4/backup-key-check.txt) | 덤프 안 실제 키 문자열 개수(모두 0) |
| [day4/restore-run.txt](../evidence/day4/restore-run.txt) | 임시 컨테이너 복구 시험 출력(9/9 일치) |
