from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import AppException, app_exception_handler
from app.core.middleware import RequestIdMiddleware
from app.routers import (
    health,
    meta,
    users,
    profile,
    weather,
    analysis,
    recommendations,
    savings,
    calculations,
    internal,
)

app = FastAPI(
    title="CoolLink AI API",
    description="AI 생활패턴 판단 + 시간대별 날씨 + 집 환경 기반 탄소중립 절약 추천 서비스",
    version="0.3.0",
)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware
app.add_middleware(RequestIdMiddleware)

# Routers
app.include_router(health.router, tags=["Health"])
app.include_router(meta.router, prefix="/api/v1/meta", tags=["Meta"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["Profile"])
app.include_router(weather.router, prefix="/api/v1/weather", tags=["Weather"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["Recommendations"])
app.include_router(savings.router, prefix="/api/v1/savings", tags=["Savings"])
app.include_router(calculations.router, prefix="/api/v1/calculations", tags=["Calculations"])
app.include_router(internal.router, prefix="/api/v1/internal", tags=["Internal"])
