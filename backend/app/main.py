"""FastAPI application factory for Cortexa Labs backend."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
from app.routers import leads, campaigns, inboxes, analytics, auth, tracking, settings as settings_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Cortexa Labs — Cold Email API",
        description="AI-powered cold email automation for Cortexa Labs",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(leads.router, prefix="/api/leads", tags=["leads"])
    app.include_router(campaigns.router, prefix="/api/campaigns", tags=["campaigns"])
    app.include_router(inboxes.router, prefix="/api/inboxes", tags=["inboxes"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
    app.include_router(tracking.router, prefix="/track", tags=["tracking"])
    app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "Cortexa Labs API"}

    return app


app = create_app()
