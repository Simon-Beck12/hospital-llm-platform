"""키 기반 계정 식별과 5분 캐시 테스트. 업스트림(LiteLLM)은 httpx.MockTransport로 흉내 낸다."""

from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.identity import IdentityCache, get_identity_cache, key_hash
from app.main import app
from app.proxy import get_http_client

API_KEY = "sk-test-identity"
AUTH = {"Authorization": f"Bearer {API_KEY}"}
KEY_INFO = {"key": "hashed", "info": {"user_id": "researcher_a", "key_alias": "researcher_a"}}


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class KeyInfoUpstream:
    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []
        self.status = 200

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/key/info"
        self.calls.append(request)
        if self.status != 200:
            return httpx.Response(self.status, json={"error": {"message": "Authentication Error"}})
        return httpx.Response(200, json=KEY_INFO)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def cache(clock: FakeClock) -> IdentityCache:
    return IdentityCache(ttl_s=300.0, max_size=1000, clock=clock)


@pytest.fixture
def upstream(cache: IdentityCache) -> Iterator[KeyInfoUpstream]:
    up = KeyInfoUpstream()
    mock_client = httpx.AsyncClient(
        transport=httpx.MockTransport(up), base_url="http://litellm.test"
    )
    app.dependency_overrides[get_http_client] = lambda: mock_client
    app.dependency_overrides[get_identity_cache] = lambda: cache
    yield up
    app.dependency_overrides.clear()


@pytest.fixture
def client(upstream: KeyInfoUpstream) -> TestClient:
    return TestClient(app)


def test_whoami_returns_user_id(client: TestClient, upstream: KeyInfoUpstream) -> None:
    res = client.get("/v1/whoami", headers={**AUTH, "X-Request-ID": "rid-who"})
    assert res.status_code == 200
    assert res.json() == {
        "user_id": "researcher_a",
        "key_alias": "researcher_a",
        "request_id": "rid-who",
    }
    # 요청자 본인 키로 /key/info를 부른다.
    assert upstream.calls[0].headers["authorization"] == f"Bearer {API_KEY}"


def test_same_key_hits_cache(client: TestClient, upstream: KeyInfoUpstream) -> None:
    assert client.get("/v1/whoami", headers=AUTH).status_code == 200
    assert client.get("/v1/whoami", headers=AUTH).status_code == 200
    assert len(upstream.calls) == 1


def test_cache_expires_after_ttl(
    client: TestClient, upstream: KeyInfoUpstream, clock: FakeClock
) -> None:
    client.get("/v1/whoami", headers=AUTH)
    clock.now += 301
    client.get("/v1/whoami", headers=AUTH)
    assert len(upstream.calls) == 2


def test_unknown_key_returns_401_and_is_not_cached(
    client: TestClient, upstream: KeyInfoUpstream, cache: IdentityCache
) -> None:
    upstream.status = 401
    res = client.get("/v1/whoami", headers=AUTH)
    assert res.status_code == 401
    assert res.json()["error"]["type"] == "unknown_api_key"
    assert len(cache) == 0
    assert cache.get(API_KEY) is None
    # 캐시 키는 원문이 아니라 sha256 해시다.
    assert key_hash(API_KEY) != API_KEY and len(key_hash(API_KEY)) == 64
