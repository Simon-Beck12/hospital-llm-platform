"""게이트웨이 Prometheus 지표.

라벨에는 키, 요청 ID, 프롬프트 내용, IP를 넣지 않는다(유출과 라벨 수 폭증 방지).
route는 알려진 경로만 그대로 쓰고 나머지는 "other", user는 key_alias(식별 실패 시 "unknown")다.
"""

from typing import Any

from prometheus_client import Counter, Gauge, Histogram

KNOWN_ROUTES = frozenset({"/v1/chat/completions", "/v1/models", "/v1/whoami"})
TOKEN_KINDS = ("prompt", "completion")

REQUESTS = Counter(
    "gateway_requests_total", "게이트웨이 /v1 요청 수", ["route", "status", "user"]
)
DURATION = Histogram(
    "gateway_request_duration_seconds",
    "게이트웨이 /v1 요청 처리 시간(초)",
    ["route"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
TOKENS = Counter("gateway_tokens_total", "사용자별 토큰 수", ["user", "kind"])
PII_MASKED = Counter("gateway_pii_masked_total", "종류별 PII 마스킹 건수", ["kind"])
INFLIGHT = Gauge("gateway_inflight_requests", "처리 중인 /v1 요청 수")


def route_label(path: str) -> str:
    return path if path in KNOWN_ROUTES else "other"


def observe_record(record: dict[str, Any]) -> None:
    """감사 로그 레코드의 값으로 지표를 갱신한다."""
    route = route_label(record["path"])
    user = record.get("key_alias") or "unknown"
    REQUESTS.labels(route=route, status=str(record["status"]), user=user).inc()
    DURATION.labels(route=route).observe(record["latency_ms"] / 1000)
    for kind in TOKEN_KINDS:
        n = record.get(f"{kind}_tokens")
        if isinstance(n, int) and n > 0:
            TOKENS.labels(user=user, kind=kind).inc(n)
    for kind, n in (record.get("pii_counts") or {}).items():
        if n:
            PII_MASKED.labels(kind=kind).inc(n)
