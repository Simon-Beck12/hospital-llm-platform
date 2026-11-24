import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.proxy import error_body, forward, get_http_client, lifespan

app = FastAPI(title="LLM Serving Gateway", lifespan=lifespan)


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
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
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


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
async def list_models(request: Request, auth: AuthHeader, client: HttpClient) -> JSONResponse:
    status, body = await forward(client, "GET", "/v1/models", request.state.request_id, auth)
    return JSONResponse(status_code=status, content=body)


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request, auth: AuthHeader, client: HttpClient
) -> JSONResponse:
    try:
        body = await request.json()
    except ValueError:
        raise GatewayError(400, "invalid_request", "본문이 올바른 JSON이 아닙니다") from None
    if not isinstance(body, dict):
        raise GatewayError(400, "invalid_request", "본문은 JSON 객체여야 합니다")
    if body.get("stream") is True:
        raise GatewayError(400, "stream_not_supported", "stream: true는 아직 지원하지 않습니다")
    status, resp_body = await forward(
        client, "POST", "/v1/chat/completions", request.state.request_id, auth, json_body=body
    )
    return JSONResponse(status_code=status, content=resp_body)
