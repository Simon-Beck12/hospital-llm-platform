"""감사 로그 테스트. 로그는 tmp_path에 쓰고, 업스트림은 httpx.MockTransport로 흉내 낸다."""

import json
import re
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.audit import AUDIT_FIELDS, close_audit_logger, prompt_sha256
from app.config import get_settings
from app.identity import IdentityCache, get_identity_cache
from app.main import app
from app.masking import mask_messages
from app.proxy import get_http_client

TEST_KEY = "sk-audit-test-key-0001"
AUTH = {"Authorization": f"Bearer {TEST_KEY}"}
PROMPT = "감사 로그 테스트용 질문 문장입니다"
ANSWER = "감사 로그 테스트용 응답 문장입니다"
CHAT_BODY = {"model": "qwen3-8b", "messages": [{"role": "user", "content": PROMPT}]}
USAGE = {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}
OK_RESPONSE = {"choices": [{"message": {"role": "assistant", "content": ANSWER}}], "usage": USAGE}
KEY_INFO = {"key": "hashed", "info": {"user_id": "researcher_b", "key_alias": "researcher_b"}}
HEX64 = re.compile(r"[0-9a-f]{64}")

Handler = Callable[[httpx.Request], httpx.Response]


class Upstream:
    def __init__(self) -> None:
        self.handler: Handler = lambda req: httpx.Response(200, json=OK_RESPONSE)
        self.sent_bodies: list[bytes] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/key/info":
            return httpx.Response(200, json=KEY_INFO)
        self.sent_bodies.append(request.content)
        return self.handler(request)


def _use_log_path(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setenv("GATEWAY_AUDIT_LOG_PATH", str(path))
    get_settings.cache_clear()
    close_audit_logger()


@pytest.fixture
def log_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    path = tmp_path / "logs" / "audit.jsonl"
    _use_log_path(monkeypatch, path)
    yield path
    close_audit_logger()
    get_settings.cache_clear()


@pytest.fixture
def upstream(log_path: Path) -> Iterator[Upstream]:
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


def _records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_chat_200_writes_one_full_record(client: TestClient, log_path: Path) -> None:
    res = client.post("/v1/chat/completions", json=CHAT_BODY, headers=AUTH)
    assert res.status_code == 200
    records = _records(log_path)
    assert len(records) == 1
    rec = records[0]
    assert set(rec) == set(AUDIT_FIELDS)
    assert rec["status"] == 200
    assert rec["user_id"] == "researcher_b"
    assert rec["model"] == "qwen3-8b"
    assert rec["total_tokens"] == 18
    assert rec["prompt_tokens"] == 11 and rec["completion_tokens"] == 7
    assert HEX64.fullmatch(rec["prompt_sha256"])
    assert rec["request_id"] == res.headers["x-request-id"]
    assert isinstance(rec["latency_ms"], int)
    assert rec["ts"].endswith("Z")
    assert log_path.stat().st_mode & 0o777 == 0o600
    assert log_path.parent.stat().st_mode & 0o777 == 0o700


def test_log_has_no_body_auth_or_key(client: TestClient, log_path: Path) -> None:
    client.post("/v1/chat/completions", json=CHAT_BODY, headers=AUTH)
    text = log_path.read_text(encoding="utf-8")
    assert PROMPT not in text
    assert ANSWER not in text
    assert "Bearer" not in text
    assert TEST_KEY not in text


def test_upstream_429_is_logged_with_user(
    client: TestClient, upstream: Upstream, log_path: Path
) -> None:
    upstream.handler = lambda req: httpx.Response(
        429, json={"error": {"type": "throttling_error", "message": "Rate limit exceeded"}}
    )
    res = client.post("/v1/chat/completions", json=CHAT_BODY, headers=AUTH)
    assert res.status_code == 429
    (rec,) = _records(log_path)
    assert rec["status"] == 429
    assert rec["user_id"] == "researcher_b"
    assert rec["error_type"] == "throttling_error"
    assert rec["total_tokens"] is None


def test_missing_auth_is_logged_as_401(client: TestClient, log_path: Path) -> None:
    res = client.post("/v1/chat/completions", json=CHAT_BODY)
    assert res.status_code == 401
    (rec,) = _records(log_path)
    assert rec["status"] == 401
    assert rec["user_id"] is None
    assert rec["error_type"] == "missing_api_key"


def test_healthz_is_not_logged(client: TestClient, log_path: Path) -> None:
    assert client.get("/healthz").status_code == 200
    assert _records(log_path) == []


def test_pii_counts_and_masked_hash(client: TestClient, log_path: Path) -> None:
    messages = [{"role": "user", "content": "주민번호 900101-1234567 확인"}]
    res = client.post(
        "/v1/chat/completions", json={"model": "qwen3-8b", "messages": messages}, headers=AUTH
    )
    assert res.status_code == 200
    text = log_path.read_text(encoding="utf-8")
    assert "900101" not in text
    (rec,) = _records(log_path)
    assert rec["pii_counts"]["rrn"] == 1
    assert rec["pii_total"] == 1
    masked, _ = mask_messages(messages)
    assert rec["prompt_sha256"] == prompt_sha256(masked)
    assert rec["prompt_sha256"] != prompt_sha256(messages)


def test_unwritable_log_path_does_not_break_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("파일이 폴더 자리를 막고 있다")
    _use_log_path(monkeypatch, blocker / "audit.jsonl")
    res = client.post("/v1/chat/completions", json=CHAT_BODY, headers=AUTH)
    assert res.status_code == 200
