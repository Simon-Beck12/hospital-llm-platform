# hospital-llm-platform

사내 연구자용 LLM 서빙 플랫폼이다.
PC 1대(RTX 5090)와 폐쇄망을 가정한다.

## 구성

| 구성요소 | 역할 |
|---|---|
| vLLM | 모델 추론 서버 (OpenAI 호환 API) |
| LiteLLM | API 키, 사용자별 한도(RPM/TPM), 사용량 집계 |
| FastAPI 게이트웨이 | 인증, PII 마스킹, 감사 로그, 요청 ID |
| Docker Compose | 전체 서비스 배포 |
| Prometheus / Grafana | 지표 수집과 대시보드 |

## 빠른 시작

```bash
uv sync
cp .env.example .env   # 값을 채운다
uv run uvicorn app.main:app --reload
uv run pytest
```

## 진행 상황

- [ ] 1일차: vLLM + LiteLLM + Docker Compose
- [ ] 2일차: FastAPI 게이트웨이
- [ ] 3일차: 모니터링과 부하 테스트
- [ ] 4일차: 폐쇄망 배포와 백업
