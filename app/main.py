from fastapi import FastAPI

app = FastAPI(title="LLM Serving Gateway")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
