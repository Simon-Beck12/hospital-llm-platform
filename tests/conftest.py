"""모든 테스트 공통 설정."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.audit import close_audit_logger
from app.config import get_settings


@pytest.fixture(autouse=True)
def isolated_audit_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """감사 로그를 테스트마다 tmp_path로 보낸다. 저장소 logs/audit.jsonl에 쓰지 않는다."""
    monkeypatch.setenv("GATEWAY_AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
    get_settings.cache_clear()
    close_audit_logger()
    yield
    close_audit_logger()
    get_settings.cache_clear()
