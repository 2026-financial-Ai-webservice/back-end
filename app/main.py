from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine
from app.core.redis import close_redis
from app.domain.company.router import router as company_router
from app.domain.portfolio.router import router as portfolio_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 필요 시 startup 로직 (배치 스케줄러 등록 등)
    yield
    await close_redis()
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 배포 시 프론트 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(company_router)
app.include_router(portfolio_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.ENV}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "timestamp": datetime.now(UTC).isoformat(),
            "status": 400,
            "error": "Illegal Argument",
            "message": str(exc.errors()),
            "path": request.url.path,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "timestamp": datetime.now(UTC).isoformat(),
            "status": exc.status_code,
            "error": (
                "Illegal Argument"
                if exc.status_code == 400
                else "Request Error"
            ),
            "message": str(exc.detail),
            "path": request.url.path,
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "timestamp": datetime.now(UTC).isoformat(),
            "status": 500,
            "error": "Server Error",
            "message": str(exc) or "서버 오류가 발생했습니다.",
            "path": request.url.path,
        },
    )
