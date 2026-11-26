# 폐쇄망 기동 시험 (2026-11-26)

인터넷이 끊긴 상태에서도 스택이 다시 켜지고 응답하는지 확인했다.

## 시험 방법

1. 사용자가 서버 바탕화면(GNOME)에서 유선 연결을 끈다. SSH도 끊길 수 있으므로 서버 앞에서 직접 한다.
2. 서버 터미널에서 [scripts/offline_check.sh](../scripts/offline_check.sh)를 인자 없이 실행한다. 스크립트가 하는 일은 다음과 같다.
   - 인터넷 차단을 확인한다. `curl https://huggingface.co`와 `getent hosts github.com`이 둘 다 실패해야 한다. 연결돼 있으면 "시험 무효"를 출력하고 종료 코드 2로 끝난다.
   - `docker compose stop` → `start` 후 10초마다 7개 컨테이너의 running·healthy 여부를 본다.
   - researcher_a 키로 `/v1/whoami`와 chat을 보낸다. Prometheus 타깃 4개를 확인하고, 외부 접속 관련 로그를 뽑는다.
3. 판정 줄("판정: 통과" 또는 "판정: 실패(이유)")을 확인하고 유선을 다시 켠다. 온라인 예행연습은 `--allow-online`으로 돌린다.

## 결과

| 항목 | 온라인(예행연습) | 오프라인 |
|---|---|---|
| 차단 확인 | huggingface 연결됨, github DNS 성공 | huggingface 실패, github DNS 실패 |
| 전부 정상까지(초) | 61 | 61 |
| whoami | 200 (0.069초) | 200 (0.068초) |
| chat (max_tokens 16) | 200 (0.345초) | 200 (0.334초) |
| 타깃 up 수 | 4/4 | 4/4 |
| 외부 접속 로그 | 패턴 일치 10줄, 실제 외부 접속 시도 0줄 | 패턴 일치 10줄, 실제 외부 접속 시도 0줄 |
| 판정 | 통과 | 통과 |

- 측정 시각은 온라인 2026-11-26 03:14:47Z, 오프라인 03:18:22Z다. 원본: [온라인](../evidence/day4/offline-check-online.txt), [오프라인](../evidence/day4/offline-check-offline.txt)
- 로그 패턴은 `resolve|connection refused|timed out|huggingface|github|usage|telemetry`다. 일치한 10줄은 모두 오탐이었고, 접속 실패(`connection refused`, `timed out`, 이름 해석 실패) 줄은 0줄이었다.
  - 배너 문구: LiteLLM 시작 배너의 `https://github.com/BerriAI/litellm/issues/new` 2줄
  - 패키지 이름: Prometheus의 `package=github.com/KimMachineGun/automemlimit` 1줄
  - "resolve" 단어 일치: LiteLLM의 `migration resolver`, vLLM의 `Resolved architecture`, Grafana의 `Resolved storage mode` 2줄. 합쳐서 4줄
  - "usage" 단어 일치: vLLM의 GPU 메모리 점검 줄 1줄
  - Grafana 내부 모듈: `usagestats.collector` 등록, `service.UsageStats` 시작 2줄. 보고는 `GF_ANALYTICS_REPORTING_ENABLED=false`로 꺼져 있다.
- 오프라인과 온라인의 기동 시간이 같다(61초). 외부 응답을 기다리며 지연되는 구성 요소가 없다는 뜻이다.

## 끈 텔레메트리와 외부 통신

| 서비스 | 설정 | 이유 |
|---|---|---|
| vLLM | `VLLM_NO_USAGE_STATS=1`, `DO_NOT_TRACK=1` | vLLM 사용 통계 전송 끔 |
| vLLM | `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` | Hugging Face Hub 조회 끔. 모델은 `/srv/models`에서만 읽음 |
| LiteLLM | `LITELLM_TELEMETRY=False` | LiteLLM 사용 통계 전송 끔 |
| LiteLLM | `LITELLM_LOCAL_MODEL_COST_MAP=True` | 모델 가격표를 인터넷에서 받지 않고 이미지에 든 것을 씀 |
| Grafana | `GF_ANALYTICS_REPORTING_ENABLED`, `GF_ANALYTICS_CHECK_FOR_UPDATES`, `GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES`, `GF_NEWS_NEWS_FEED_ENABLED` 모두 false | 사용 보고, 업데이트 확인, 뉴스 피드 끔(3일차 설정) |

- 병원 내부 데이터가 오가는 서버이므로, 사용 통계 같은 메타데이터도 밖으로 보내지 않는다. 그리고 폐쇄망에서 외부 응답을 기다리느라 기동이 늦어지는 일을 막는다.

## 폐쇄망 반입 절차

1. 이미지: 인터넷이 되는 곳에서 `docker save`로 7개 이미지(`docker compose config --images`)를 tar로 묶어 옮기고, 서버에서 `docker load`로 넣는다. LiteLLM 이미지는 digest로 고정돼 있다.
2. 모델: Qwen3-8B 파일 전체를 `/srv/models/Qwen3-8B`로 복사하고, 크기와 해시를 대조한다.
3. 게이트웨이 빌드: `uv.lock` 기준으로 uv 캐시(또는 wheel 묶음)를 함께 옮겨 `uv sync --frozen --offline`으로 설치한다. 아니면 빌드된 gateway 이미지를 1번과 같이 옮긴다.

## 한계

- 서버 1대에서 GUI로 유선을 끊어 본 시험이다. 방화벽 정책(나가는 연결 차단)이나 실제 폐쇄망 장비 위에서 한 시험은 아니다.
