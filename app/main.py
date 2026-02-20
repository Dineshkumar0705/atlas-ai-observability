import os
import logging
import uuid
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.database import Base, check_database_connection

# ---------------------------------------------------
# FORCE MODEL REGISTRATION (CRITICAL FOR ALEMBIC)
# ---------------------------------------------------
import app.models  # noqa

from app.api.routes import router as atlas_router
from app.api.config_routes import router as config_router
from app.api.billing_routes import router as billing_router


# ===================================================
# 🔧 Configuration
# ===================================================

SERVICE_NAME = "ATLAS Trust Engine"
ATLAS_VERSION = "0.5.0"

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
DEBUG_MODE = ENVIRONMENT != "production"

ENABLE_BILLING = os.getenv("ENABLE_BILLING", "true").lower() == "true"

RAW_ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = (
    RAW_ALLOWED_ORIGINS.split(",")
    if RAW_ALLOWED_ORIGINS != "*"
    else ["*"]
)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")


# ===================================================
# 📝 Logging
# ===================================================

LOG_LEVEL = logging.INFO if DEBUG_MODE else logging.WARNING

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("ATLAS")


# ===================================================
# 🚀 Lifespan Manager
# ===================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("🚀 Booting ATLAS Trust Engine")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Version: {ATLAS_VERSION}")

    if DEBUG_MODE:
        logger.info(
            f"📊 Registered tables: {list(Base.metadata.tables.keys())}"
        )

    # -------- Database Health Check --------
    try:
        db_ok = check_database_connection()
        if db_ok:
            logger.info("✅ Database connected.")
        else:
            logger.warning("⚠ Database connection failed.")
    except Exception:
        logger.exception("Database check failed (non-blocking).")

    # -------- Billing Check --------
    if ENABLE_BILLING:
        if STRIPE_SECRET_KEY:
            logger.info("💳 Billing enabled.")
        else:
            logger.warning("⚠ Billing enabled but STRIPE_SECRET_KEY missing.")

    yield

    logger.info("🛑 Shutting down ATLAS...")


# ===================================================
# 🏗 FastAPI App
# ===================================================

app = FastAPI(
    title=SERVICE_NAME,
    description="AI Trust, Hallucination & Risk Scoring Middleware",
    version=ATLAS_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if DEBUG_MODE else None,
    redoc_url="/redoc" if DEBUG_MODE else None,
)


# ===================================================
# 🌐 CORS Middleware
# ===================================================

if ENVIRONMENT == "production" and ALLOWED_ORIGINS == ["*"]:
    logger.warning("⚠ Wildcard CORS in production is unsafe.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================================================
# 📊 Request Tracing Middleware
# ===================================================

@app.middleware("http")
async def request_tracer(request: Request, call_next):

    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = datetime.utcnow()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(f"[{request_id}] Request crashed")
        raise

    duration = (datetime.utcnow() - start_time).total_seconds()

    if DEBUG_MODE:
        logger.info(
            f"[{request_id}] "
            f"{request.method} {request.url.path} "
            f"→ {response.status_code} "
            f"in {round(duration, 3)}s"
        )

    response.headers["X-Request-ID"] = request_id
    return response


# ===================================================
# 🛑 Global Exception Handler
# ===================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):

    logger.exception(f"Unhandled error at {request.url.path}")

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "service": SERVICE_NAME,
            "version": ATLAS_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# ===================================================
# 🔗 ROUTERS (ALL UNDER /atlas)
# ===================================================

app.include_router(atlas_router, prefix="/atlas", tags=["ATLAS"])
app.include_router(config_router, prefix="/atlas", tags=["Config"])
app.include_router(billing_router, prefix="/atlas", tags=["Billing"])


# -------- Stripe Conditional Load --------

if ENABLE_BILLING:
    try:
        from app.api.stripe_routes import router as stripe_router
        from app.api.stripe_webhook import router as stripe_webhook_router

        app.include_router(stripe_router, prefix="/atlas", tags=["Stripe"])
        app.include_router(stripe_webhook_router, prefix="/atlas", tags=["Stripe"])

    except Exception:
        logger.warning("Stripe not installed. Billing endpoints disabled.")


# ===================================================
# 🏠 Root
# ===================================================

@app.get("/")
def root():
    return {
        "service": SERVICE_NAME,
        "version": ATLAS_VERSION,
        "environment": ENVIRONMENT,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ===================================================
# ❤️ Liveness
# ===================================================

@app.get("/health/live")
def liveness():
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ===================================================
# 🧠 Readiness
# ===================================================

@app.get("/health/ready")
def readiness():

    try:
        db_ok = check_database_connection()
    except Exception:
        db_ok = False

    return {
        "database": "connected" if db_ok else "disconnected",
        "status": "ready" if db_ok else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
    }