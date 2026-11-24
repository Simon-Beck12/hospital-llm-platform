import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

import httpx
from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.identity import Identity, IdentityCache, get_identity_cache, resolve_identity
from app.proxy import error_body, forward, get_http_client, lifespan

app = FastAPI(title="LLM Serving Gateway", lifespan=lifespan)

REQUEST_ID_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")


class GatewayError(Exception):
    def __init__(self, status_code: int, error_type: str, message: str) -> None:
        self.status_code = status_code
        self.error_type = error_type
        self.message = message


@app.exception_handler(GatewayError)
async def gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.error_type, exc.message, request.state.request_id),
    )


@app.middleware("http")
async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    incoming = request.headers.get("x-request-id", "")
    request_id = incoming if REQUEST_ID_RE.fullmatch(incoming) else uuid.uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def require_bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer ") or not auth[len("Bearer ") :].strip():
        raise GatewayError(401, "missing_api_key", "Authorization: Bearer <키> 헤더가 필요합니다")
    return auth


AuthHeader = Annotated[str, Depends(require_bearer)]
HttpClient = Annotated[httpx.AsyncClient, Depends(get_http_client)]
Cache = Annotated[IdentityCache, Depends(get_identity_cache)]


async def identify(
    request: Request, auth: AuthHeader, client: HttpClient, cache: Cache
) -> Identity | None:
    """요청자 키로 계정을 찾아 request.state에 둔다. 실패해도 요청은 막지 않는다."""
    api_key = auth[len("Bearer ") :].strip()
    identity = await resolve_identity(client, api_key, request.state.request_id, cache)
    request.state.user_id = (identity and identity.user_id) or "unknown"
    request.state.key_alias = (identity and identity.key_alias) or "unknown"
    return identity


Identified = Annotated[Identity | None, Depends(identify)]


def strip_leading_whitespace(body: Any) -> None:
    """choices[*].message.content 앞쪽 줄바꿈·공백만 제거한다."""
    if not isinstance(body, dict) or not isinstance(body.get("choices"), list):
        return
    for choice in body["choices"]:
        message = choice.get("message") if isinstance(choice, dict) else None
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            message["content"] = message["content"].lstrip()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/whoami")
async def whoami(request: Request, identity: Identified) -> dict[str, str | None]:
    if identity is None:
        raise GatewayError(401, "unknown_api_key", "API 키로 계정을 확인할 수 없습니다")
    return {
        "user_id": identity.user_id,
        "key_alias": identity.key_alias,
        "request_id": request.state.request_id,
    }


@app.get("/v1/models")
async def list_models(
    request: Request, auth: AuthHeader, client: HttpClient, _: Identified
) -> JSONResponse:
    status, body, headers = await forward(
        client, "GET", "/v1/models", request.state.request_id, auth
    )
    return JSONResponse(status_code=status, content=body, headers=headers)


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request, auth: AuthHeader, client: HttpClient, _: Identified
) -> JSONResponse:
    try:
        body = await request.json()
    except ValueError:
        raise GatewayError(400, "invalid_request", "본문이 올바른 JSON이 아닙니다") from None
    if not isinstance(body, dict):
        raise GatewayError(400, "invalid_request", "본문은 JSON 객체여야 합니다")
    if body.get("stream") is True:
        raise GatewayError(400, "stream_not_supported", "stream: true는 아직 지원하지 않습니다")
    status, resp_body, headers = await forward(
        client, "POST", "/v1/chat/completions", request.state.request_id, auth, json_body=body
    )
    if status == 200:
        strip_leading_whitespace(resp_body)
    return JSONResponse(status_code=status, content=resp_body, headers=headers)
