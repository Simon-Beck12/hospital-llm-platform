"""요청자 API 키로 계정을 식별한다.

LiteLLM GET /key/info 를 요청자 본인 키로 불러 user_id, key_alias를 얻고 5분간 캐시한다.
캐시 키는 sha256 해시만 쓴다. 키 원문은 저장하거나 기록하지 않는다.
"""

import hashlib
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class Identity:
    user_id: str | None
    key_alias: str | None


def key_hash(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


class IdentityCache:
    """TTL·최대 개수 제한이 있는 캐시. 넘치면 가장 오래 안 쓴 항목부터 버린다."""

    def __init__(
        self,
        ttl_s: float = 300.0,
        max_size: int = 1000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.ttl_s = ttl_s
        self.max_size = max_size
        self._clock = clock
        self._data: OrderedDict[str, tuple[float, Identity]] = OrderedDict()

    def get(self, api_key: str) -> Identity | None:
        k = key_hash(api_key)
        item = self._data.get(k)
        if item is None:
            return None
        expires_at, identity = item
        if self._clock() >= expires_at:
            del self._data[k]
            return None
        self._data.move_to_end(k)
        return identity

    def set(self, api_key: str, identity: Identity) -> None:
        k = key_hash(api_key)
        self._data[k] = (self._clock() + self.ttl_s, identity)
        self._data.move_to_end(k)
        while len(self._data) > self.max_size:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)


identity_cache = IdentityCache()


def get_identity_cache() -> IdentityCache:
    """FastAPI 의존성. 테스트에서 dependency_overrides로 바꾼다."""
    return identity_cache


async def resolve_identity(
    client: httpx.AsyncClient,
    api_key: str,
    request_id: str,
    cache: IdentityCache | None = None,
) -> Identity | None:
    """캐시 → LiteLLM /key/info(본인 키) 순으로 계정을 찾는다. 실패하면 None(캐시 안 함)."""
    cache = identity_cache if cache is None else cache
    cached = cache.get(api_key)
    if cached is not None:
        return cached
    try:
        resp = await client.get(
            "/key/info",
            headers={"Authorization": f"Bearer {api_key}", "X-Request-ID": request_id},
        )
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    try:
        info = resp.json().get("info") or {}
    except (ValueError, AttributeError):
        return None
    identity = Identity(user_id=info.get("user_id"), key_alias=info.get("key_alias"))
    cache.set(api_key, identity)
    return identity
