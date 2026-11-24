"""LiteLLM 중계: 공유 HTTP 클라이언트와 forward()."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request

from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    async with httpx.AsyncClient(
        base_url=settings.litellm_base_url, timeout=settings.upstream_timeout_s
    ) as client:
        app.state.http = client
        yield


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


def error_body(error_type: str, message: str, request_id: str) -> dict[str, Any]:
    return {"error": {"type": error_type, "message": message, "request_id": request_id}}


def pass_through_headers(headers: httpx.Headers) -> dict[str, str]:
    """업스트림 응답 헤더 중 Retry-After와 x-ratelimit-* 만 고른다."""
    return {
        k: v
        for k, v in headers.items()
        if k.lower() == "retry-after" or k.lower().startswith("x-ratelimit-")
    }


async def forward(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    request_id: str,
    auth_header: str,
    json_body: Any = None,
) -> tuple[int, Any, dict[str, str]]:
    """LiteLLM으로 요청을 보내고 (상태 코드, JSON 본문, 전달할 헤더)를 돌려준다."""
    headers = {"Authorization": auth_header, "X-Request-ID": request_id}
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    try:
        resp = await client.request(method, path, headers=headers, json=json_body)
    except httpx.TimeoutException:
        return 504, error_body("upstream_timeout", "LiteLLM 응답 시간 초과", request_id), {}
    except httpx.TransportError:
        # ConnectError 외의 연결 계열 오류(연결 끊김 등)도 502로 묶는다.
        body = error_body("upstream_unavailable", "LiteLLM에 연결할 수 없습니다", request_id)
        return 502, body, {}
    extra = pass_through_headers(resp.headers)
    try:
        return resp.status_code, resp.json(), extra
    except ValueError:
        body = error_body("upstream_bad_response", "LiteLLM 응답이 JSON이 아닙니다", request_id)
        return 502, body, extra
