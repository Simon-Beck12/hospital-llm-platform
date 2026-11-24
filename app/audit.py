"""감사 로그: /v1/* 요청마다 JSON 한 줄.

본문(프롬프트·응답), Authorization 헤더, API 키 원문·해시는 남기지 않는다.
프롬프트는 마스킹이 끝난 messages의 sha256만 남긴다.
로그 쓰기가 실패해도 요청은 실패시키지 않는다.
"""

import hashlib
import json
import logging
import os
import sys
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from typing import Any

from app.config import get_settings

LOGGER_NAME = "gateway.audit"

AUDIT_FIELDS = (
    "ts",
    "request_id",
    "user_id",
    "key_alias",
    "method",
    "path",
    "status",
    "latency_ms",
    "model",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "pii_counts",
    "pii_total",
    "prompt_sha256",
    "error_type",
    "client_ip",
)


def _report_failure(exc: BaseException) -> None:
    # 예외 이름만 출력한다. 레코드나 경로 등 다른 내용은 출력하지 않는다.
    print(f"audit write failed: {type(exc).__name__}", file=sys.stderr)


class _PrivateRotatingFileHandler(RotatingFileHandler):
    """파일을 새로 열 때마다(회전 포함) 권한을 600으로 맞춘다."""

    def _open(self):  # type: ignore[override]
        stream = super()._open()
        os.chmod(self.baseFilename, 0o600)
        return stream

    def handleError(self, record: logging.LogRecord) -> None:
        # 기본 동작은 레코드 내용까지 stderr에 찍으므로 예외 이름만 남긴다.
        _report_failure(sys.exc_info()[1] or RuntimeError("unknown"))


_logger = logging.getLogger(LOGGER_NAME)
_logger.setLevel(logging.INFO)
_logger.propagate = False
_configured_for: tuple[str, int, int] | None = None


def _ensure_handler() -> logging.Logger:
    """현재 설정의 경로로 핸들러를 준비한다. 경로가 바뀌면 다시 만든다."""
    global _configured_for
    s = get_settings()
    wanted = (os.path.abspath(s.audit_log_path), s.audit_log_max_bytes, s.audit_log_backup_count)
    if _configured_for == wanted and _logger.handlers:
        return _logger
    close_audit_logger()
    path, max_bytes, backup_count = wanted
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder, mode=0o700, exist_ok=True)
        os.chmod(folder, 0o700)
    handler = _PrivateRotatingFileHandler(
        path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)
    _configured_for = wanted
    return _logger


def close_audit_logger() -> None:
    global _configured_for
    for h in list(_logger.handlers):
        _logger.removeHandler(h)
        h.close()
    _configured_for = None


def utc_ts() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def prompt_sha256(messages: Any) -> str:
    """마스킹이 끝난 messages의 정규화 JSON sha256 hex."""
    canonical = json.dumps(messages, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_audit(record: dict[str, Any]) -> None:
    try:
        line = json.dumps(record, ensure_ascii=False)
        _ensure_handler().info(line)
    except Exception as exc:  # noqa: BLE001 - 감사 로그 실패가 요청을 깨면 안 된다
        _report_failure(exc)
