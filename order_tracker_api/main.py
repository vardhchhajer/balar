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
from app.routers.outstanding import router as outstanding_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_database()
    yield


app = FastAPI(
    title="Baalar API",
    version="2.0.0",
    description="Baalar - B2B Order & Outstanding Tracking API",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(orders_router)
app.include_router(profile_router)
app.include_router(admin_router)
app.include_router(outstanding_router)


@app.get("/", summary="Health check")
async def health_check():
    return {"status": "ok", "app": "Baalar API", "version": "2.0.0"}
