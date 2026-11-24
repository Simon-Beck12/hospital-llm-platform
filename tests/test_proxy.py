"""게이트웨이 중계 테스트. 업스트림(LiteLLM)은 httpx.MockTransport로 흉내 낸다."""

import re
from collections.abc import Callable, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.identity import IdentityCache, get_identity_cache
from app.main import app
from app.proxy import get_http_client

AUTH = "Bearer sk-test-dummy"
CHAT_BODY = {"model": "qwen3-8b", "messages": [{"role": "user", "content": "hi"}]}
OK_RESPONSE = {"choices": [{"message": {"role": "assistant", "content": "안녕하세요"}}]}
KEY_INFO = {"key": "hashed", "info": {"user_id": "tester", "key_alias": "tester"}}
HEX32 = re.compile(r"[0-9a-f]{32}")

Handler = Callable[[httpx.Request], httpx.Response]


class Upstream:
    """업스트림이 받은 요청을 기록하고, 지정한 handler로 응답한다.

    /key/info(계정 식별)는 key_info_calls에 따로 기록하고, 나머지는 calls에 기록한다.
    """

    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []
        self.key_info_calls: list[httpx.Request] = []
        self.handler: Handler = lambda req: httpx.Response(200, json=OK_RESPONSE)
        self.key_info_handler: Handler = lambda req: httpx.Response(200, json=KEY_INFO)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/key/info":
            self.key_info_calls.append(request)
            return self.key_info_handler(request)
        self.calls.append(request)
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


def test_missing_auth_returns_401_without_upstream_call(
    client: TestClient, upstream: Upstream
) -> None:
    res = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert res.status_code == 401
    assert res.json()["error"]["type"] == "missing_api_key"
    assert res.headers["x-request-id"]
    assert len(upstream.calls) == 0


def test_forward_ok_keeps_auth_and_sets_request_id(
    client: TestClient, upstream: Upstream
) -> None:
    res = client.post("/v1/chat/completions", json=CHAT_BODY, headers={"Authorization": AUTH})
    assert res.status_code == 200
    assert res.json() == OK_RESPONSE
    assert res.headers["x-request-id"]
    assert len(upstream.calls) == 1
    sent = upstream.calls[0]
    assert sent.url.path == "/v1/chat/completions"
    assert sent.headers["authorization"] == AUTH
    assert sent.headers["x-request-id"] == res.headers["x-request-id"]


def test_client_request_id_is_propagated(client: TestClient, upstream: Upstream) -> None:
    res = client.get(
        "/v1/models", headers={"Authorization": AUTH, "X-Request-ID": "client-rid-123"}
    )
    assert res.status_code == 200
    assert res.headers["x-request-id"] == "client-rid-123"
    assert upstream.calls[0].headers["x-request-id"] == "client-rid-123"


def test_upstream_429_is_passed_through(client: TestClient, upstream: Upstream) -> None:
    limit_body = {"error": {"message": "Rate limit exceeded", "code": "429"}}
    upstream.handler = lambda req: httpx.Response(429, json=limit_body)
    res = client.post("/v1/chat/completions", json=CHAT_BODY, headers={"Authorization": AUTH})
    assert res.status_code == 429
    assert res.json() == limit_body


def test_connect_error_returns_502(client: TestClient, upstream: Upstream) -> None:
    def fail(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=req)

    upstream.handler = fail
    res = client.post(
        "/v1/chat/completions",
        json=CHAT_BODY,
        headers={"Authorization": AUTH, "X-Request-ID": "rid-502"},
    )
    assert res.status_code == 502
    err = res.json()["error"]
    assert err["type"] == "upstream_unavailable"
    assert err["request_id"] == "rid-502"


def test_timeout_returns_504(client: TestClient, upstream: Upstream) -> None:
    def slow(req: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=req)

    upstream.handler = slow
    res = client.post("/v1/chat/completions", json=CHAT_BODY, headers={"Authorization": AUTH})
    assert res.status_code == 504
    assert res.json()["error"]["type"] == "upstream_timeout"


def test_stream_true_is_rejected_without_upstream_call(
    client: TestClient, upstream: Upstream
) -> None:
    res = client.post(
        "/v1/chat/completions",
        json={**CHAT_BODY, "stream": True},
        headers={"Authorization": AUTH},
    )
    assert res.status_code == 400
    assert res.json()["error"]["type"] == "stream_not_supported"
    assert len(upstream.calls) == 0


def test_invalid_request_id_is_replaced(client: TestClient, upstream: Upstream) -> None:
    res = client.get("/v1/models", headers={"Authorization": AUTH, "X-Request-ID": "a b!@#"})
    assert res.status_code == 200
    new_id = res.headers["x-request-id"]
    assert HEX32.fullmatch(new_id)
    assert upstream.calls[0].headers["x-request-id"] == new_id


def test_too_long_request_id_is_replaced(client: TestClient, upstream: Upstream) -> None:
    long_id = "a" * 65
    res = client.get("/v1/models", headers={"Authorization": AUTH, "X-Request-ID": long_id})
    new_id = res.headers["x-request-id"]
    assert new_id != long_id
    assert HEX32.fullmatch(new_id)
    assert upstream.calls[0].headers["x-request-id"] == new_id


def test_retry_after_is_passed_through(client: TestClient, upstream: Upstream) -> None:
    upstream.handler = lambda req: httpx.Response(
        429,
        json={"error": {"message": "Rate limit exceeded"}},
        headers={"Retry-After": "30", "x-ratelimit-remaining-requests": "0", "X-Other": "no"},
    )
    res = client.post("/v1/chat/completions", json=CHAT_BODY, headers={"Authorization": AUTH})
    assert res.status_code == 429
    assert res.headers["retry-after"] == "30"
    assert res.headers["x-ratelimit-remaining-requests"] == "0"
    assert "x-other" not in res.headers


def test_leading_newlines_are_stripped(client: TestClient, upstream: Upstream) -> None:
    upstream.handler = lambda req: httpx.Response(
        200, json={"choices": [{"message": {"role": "assistant", "content": "\n\n안녕\n"}}]}
    )
    res = client.post("/v1/chat/completions", json=CHAT_BODY, headers={"Authorization": AUTH})
    assert res.status_code == 200
    assert res.json()["choices"][0]["message"]["content"] == "안녕\n"
