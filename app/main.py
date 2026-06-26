import uuid

from fastapi import FastAPI, Request

from app.core.config import settings
from app.core.errors import ApiException, api_exception_handler
from app.routers.ai import router as ai_router
from app.routers.internal import router as internal_router
from app.routers.recommendations import router as recommendations_router
from app.routers.savings import router as savings_router


app = FastAPI(title=settings.app_name)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-Id") or f"req_{uuid.uuid4().hex[:12]}"
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
    return response


app.add_exception_handler(ApiException, api_exception_handler)
app.include_router(ai_router, prefix="/api/v1")
app.include_router(internal_router, prefix="/api/v1")
app.include_router(recommendations_router, prefix="/api/v1")
app.include_router(savings_router, prefix="/api/v1")
