from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.mock.seed_data import seed_database
from app.routers.auth import router as auth_router
from app.routers.orders import router as orders_router
from app.routers.profile import router as profile_router
from app.routers.admin import router as admin_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_database()
    yield


app = FastAPI(
    title="Balar API",
    version="2.0.0",
    description="B2B Order Tracking API - Balar",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(orders_router)
app.include_router(profile_router)
app.include_router(admin_router)


@app.get("/", summary="Health check")
async def health_check():
    return {"status": "ok", "app": "Balar API", "version": "2.0.0"}
