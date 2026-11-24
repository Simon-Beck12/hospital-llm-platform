import re
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

import httpx
from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.audit import prompt_sha256, utc_ts, write_audit
from app.config import get_settings
from app.identity import Identity, IdentityCache, get_identity_cache, resolve_identity
from app.masking import mask_messages
from app.proxy import error_body, forward, get_http_client, lifespan

app = FastAPI(title="LLM Serving Gateway", lifespan=lifespan)

REQUEST_ID_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")
CHAT_PATH = "/v1/chat/completions"


class GatewayError(Exception):
    def __init__(self, status_code: int, error_type: str, message: str) -> None:
        self.status_code = status_code
        self.error_type = error_type
        self.message = message


@app.exception_handler(GatewayError)
async def gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
    request.state.error_type = exc.error_type
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.error_type, exc.message, request.state.request_id),
    )


def _audit_record(request: Request, status: int, started: float) -> dict[str, Any]:
    st = request.state
    identity: Identity | None = st.identity
    usage = st.usage if isinstance(st.usage, dict) else {}
    pii_counts = dict(st.pii_counts)
    return {
        "ts": utc_ts(),
        "request_id": st.request_id,
        "user_id": identity.user_id if identity else None,
        "key_alias": identity.key_alias if identity else None,
        "method": request.method,
        "path": request.url.path,
        "status": status,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "model": st.model,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "pii_counts": pii_counts,
        "pii_total": sum(pii_counts.values()),
        "prompt_sha256": st.prompt_sha256,
        "error_type": st.error_type,
        "client_ip": request.client.host if request.client else None,
    }


@app.middleware("http")
async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    started = time.perf_counter()
    incoming = request.headers.get("x-request-id", "")
    request_id = incoming if REQUEST_ID_RE.fullmatch(incoming) else uuid.uuid4().hex
    st = request.state
    st.request_id = request_id
    st.pii_counts = {}
    st.identity = None
    st.model = None
    st.usage = None
    st.prompt_sha256 = None
    st.error_type = None
    audited = request.url.path.startswith("/v1/")
    try:
        response = await call_next(request)
    except Exception:
        if audited:
            st.error_type = st.error_type or "internal_error"
            write_audit(_audit_record(request, 500, started))
        raise
    response.headers["X-Request-ID"] = request_id
    if request.url.path == CHAT_PATH:
        # 건수만 남긴다. 401·400·429 등 오류 응답에도 넣는다(가리기 전이면 0).
        response.headers["X-PII-Masked"] = str(sum(st.pii_counts.values()))
    if audited:
        write_audit(_audit_record(request, response.status_code, started))
    return response


def _record_upstream(request: Request, status: int, body: Any) -> None:
    """감사 로그용으로 usage와 error.type을 request.state에 둔다."""
    if not isinstance(body, dict):
        return
    if isinstance(body.get("usage"), dict):
        request.state.usage = body["usage"]
    error = body.get("error")
    if status >= 400 and isinstance(error, dict) and isinstance(error.get("type"), str):
        request.state.error_type = error["type"]


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
    request.state.identity = identity
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
    _record_upstream(request, status, body)
    return JSONResponse(status_code=status, content=body, headers=headers)


@app.post(CHAT_PATH)
async def chat_completions(
    request: Request, auth: AuthHeader, client: HttpClient, _: Identified
) -> JSONResponse:
    try:
        body = await request.json()
    except ValueError:
        raise GatewayError(400, "invalid_request", "본문이 올바른 JSON이 아닙니다") from None
    if not isinstance(body, dict):
        raise GatewayError(400, "invalid_request", "본문은 JSON 객체여야 합니다")
    if isinstance(body.get("model"), str):
        request.state.model = body["model"]
    if body.get("stream") is True:
        raise GatewayError(400, "stream_not_supported", "stream: true는 아직 지원하지 않습니다")
    if get_settings().pii_masking and isinstance(body.get("messages"), list):
        masked, counts = mask_messages(body["messages"])
        body = {**body, "messages": masked}
        request.state.pii_counts = counts
    # 해시는 마스킹이 끝난 messages 기준이다.
    request.state.prompt_sha256 = prompt_sha256(body.get("messages"))
    status, resp_body, headers = await forward(
        client, "POST", CHAT_PATH, request.state.request_id, auth, json_body=body
    )
    _record_upstream(request, status, resp_body)
    if status == 200:
        strip_leading_whitespace(resp_body)
    return JSONResponse(status_code=status, content=resp_body, headers=headers)
