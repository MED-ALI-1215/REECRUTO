from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.core.logging import get_logger, setup_logging
from app.api.routes import auth, candidates, dashboard, interviews, jobs, admin

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    from app.db.session import create_all_tables
    create_all_tables()
    logger.info("REECRUTO API started")
    yield
    logger.info("REECRUTO API shutting down")


app = FastAPI(
    title="REECRUTO API",
    version="1.0.0",
    description="AI-powered recruitment platform — backend API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://localhost:8501", "http://localhost:8502",
                   "http://localhost:8503", "http://localhost:8504",
                   "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("AppError %s on %s %s: %s",
                   type(exc).__name__, request.method, request.url.path, exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})


app.include_router(auth.router,       prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(jobs.router,       prefix="/api")
app.include_router(interviews.router, prefix="/api")
app.include_router(dashboard.router,  prefix="/api")
app.include_router(admin.router,      prefix="/api")


@app.get("/health", tags=["health"])
def health():
    from app.core.config import get_settings
    settings = get_settings()
    return {
        "status": "ok",
        "groq_key_set": bool(settings.GROQ_API_KEY),
        "db_url": settings.DATABASE_URL.split("@")[-1],
        "chroma_mode": "server" if settings.CHROMA_USE_SERVER else "local",
    }
