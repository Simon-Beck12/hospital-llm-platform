"""게이트웨이 Prometheus 지표 테스트.

지표는 프로세스 전역이므로 요청 전후 값의 차이로 비교한다(테스트 순서 영향 없음).
"""

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.identity import IdentityCache, get_identity_cache
from app.main import app
from app.metrics import init_metrics
from app.proxy import get_http_client

TEST_KEY = "sk-metrics-test-key-0001"
AUTH = {"Authorization": f"Bearer {TEST_KEY}"}
ALIAS = "researcher_a"
CHAT_PATH = "/v1/chat/completions"
CHAT_BODY = {"model": "qwen3-8b", "messages": [{"role": "user", "content": "hi"}]}
USAGE = {"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17}
OK_RESPONSE = {"choices": [{"message": {"role": "assistant", "content": "ok"}}], "usage": USAGE}
KEY_INFO = {"key": "hashed", "info": {"user_id": ALIAS, "key_alias": ALIAS}}

Handler = Callable[[httpx.Request], httpx.Response]


class Upstream:
    def __init__(self) -> None:
        self.handler: Handler = lambda req: httpx.Response(200, json=OK_RESPONSE)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/key/info":
            return httpx.Response(200, json=KEY_INFO)
        return self.handler(request)


@pytest.fixture
def upstream() -> Iterator[Upstream]:
    up = Upstream()
    mock_client = httpx.AsyncClient(
        transport=httpx.MockTransport(up), base_url="http://litellm.test"
    )
    cache = IdentityCache()
    app.dependency_overrides[get_http_client] = lambda: mock_client
    app.dependency_overrides[get_identity_cache] = lambda: cache
    yield up
    app.dependency_overrides.clear()


@pytest.fixture
def client(upstream: Upstream) -> TestClient:
    return TestClient(app)


def value(name: str, **labels: str) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


def requests_total(route: str, status: str, user: str) -> float:
    return value("gateway_requests_total", route=route, status=status, user=user)


def all_requests_total() -> float:
    total = 0.0
    for metric in REGISTRY.collect():
        if metric.name == "gateway_requests":
            total += sum(s.value for s in metric.samples if s.name == "gateway_requests_total")
    return total


def test_chat_200_counts_request_and_tokens(client: TestClient) -> None:
    before = requests_total(CHAT_PATH, "200", ALIAS)
    p_before = value("gateway_tokens_total", user=ALIAS, kind="prompt")
    c_before = value("gateway_tokens_total", user=ALIAS, kind="completion")
    assert client.post(CHAT_PATH, json=CHAT_BODY, headers=AUTH).status_code == 200
    assert requests_total(CHAT_PATH, "200", ALIAS) - before == 1
    assert value("gateway_tokens_total", user=ALIAS, kind="prompt") - p_before == 12
    assert value("gateway_tokens_total", user=ALIAS, kind="completion") - c_before == 5
    assert value("gateway_inflight_requests") == 0


def test_upstream_429_counts_with_user(client: TestClient, upstream: Upstream) -> None:
    upstream.handler = lambda req: httpx.Response(
        429, json={"error": {"type": "throttling_error", "message": "Rate limit exceeded"}}
    )
    before = requests_total(CHAT_PATH, "429", ALIAS)
    assert client.post(CHAT_PATH, json=CHAT_BODY, headers=AUTH).status_code == 429
    assert requests_total(CHAT_PATH, "429", ALIAS) - before == 1


def test_missing_auth_counts_as_unknown_401(client: TestClient) -> None:
    before = requests_total(CHAT_PATH, "401", "unknown")
    assert client.post(CHAT_PATH, json=CHAT_BODY).status_code == 401
    assert requests_total(CHAT_PATH, "401", "unknown") - before == 1


def test_pii_counts_by_kind(client: TestClient) -> None:
    rrn_before = value("gateway_pii_masked_total", kind="rrn")
    phone_before = value("gateway_pii_masked_total", kind="phone")
    body = {
        "model": "qwen3-8b",
        "messages": [{"role": "user", "content": "주민 900101-1234567, 전화 010-1234-5678"}],
    }
    assert client.post(CHAT_PATH, json=body, headers=AUTH).status_code == 200
    assert value("gateway_pii_masked_total", kind="rrn") - rrn_before == 1
    assert value("gateway_pii_masked_total", kind="phone") - phone_before == 1


def test_metrics_endpoint_exposes_text_without_key(client: TestClient) -> None:
    client.post(CHAT_PATH, json=CHAT_BODY, headers=AUTH)
    res = client.get("/metrics")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain")
    assert "gateway_requests_total" in res.text
    assert TEST_KEY not in res.text


def test_metrics_and_healthz_are_not_counted_or_audited(client: TestClient) -> None:
    audit_path = Path(os.environ["GATEWAY_AUDIT_LOG_PATH"])
    lines_before = len(audit_path.read_text().splitlines()) if audit_path.exists() else 0
    before = all_requests_total()
    assert client.get("/metrics").status_code == 200
    assert client.get("/healthz").status_code == 200
    assert all_requests_total() == before
    lines_after = len(audit_path.read_text().splitlines()) if audit_path.exists() else 0
    assert lines_after == lines_before


def test_known_label_combinations_exist_at_startup() -> None:
    # app.main import(앱 시작) 때 init_metrics가 불려 0인 시계열이 이미 있다.
    sample = REGISTRY.get_sample_value(
        "gateway_requests_total",
        {"route": CHAT_PATH, "status": "429", "user": "researcher_b"},
    )
    assert sample is not None and sample >= 0
    assert REGISTRY.get_sample_value("gateway_pii_masked_total", {"kind": "mrn"}) is not None
    tokens = REGISTRY.get_sample_value(
        "gateway_tokens_total", {"user": "loadtest", "kind": "prompt"}
    )
    assert tokens is not None


def test_init_metrics_is_idempotent() -> None:
    labels = {"route": CHAT_PATH, "status": "200", "user": "admin"}
    before = REGISTRY.get_sample_value("gateway_requests_total", labels)
    init_metrics(["admin", "researcher_a", "researcher_b", "loadtest"])
    init_metrics(["admin", "researcher_a", "researcher_b", "loadtest"])
    assert REGISTRY.get_sample_value("gateway_requests_total", labels) == before
