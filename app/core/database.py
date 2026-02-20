import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# =====================================================
# 🌍 Load Environment Variables
# =====================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

if not DATABASE_URL:
    raise RuntimeError(
        "❌ DATABASE_URL is not set. Check your .env file."
    )

print(f"📦 DATABASE_URL: {DATABASE_URL}")

# =====================================================
# 🏗️ SQLAlchemy Engine (Production-Ready Config)
# =====================================================

engine = create_engine(
    DATABASE_URL,

    # ---- Connection Pool ----
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,        # Auto reconnect dead connections
    pool_recycle=1800,         # Recycle every 30 mins

    # ---- Debugging ----
    echo=False,                # Set True only for deep SQL debug
    future=True
)

# =====================================================
# 🔎 Verify Actual Connected Database (CRITICAL)
# =====================================================

try:
    with engine.connect() as conn:
        current_db = conn.execute(
            text("SELECT current_database()")
        ).scalar()

        print(f"🔥 ACTUAL CONNECTED DATABASE: {current_db}")

except Exception as e:
    print("❌ Failed to connect during engine verification.")
    raise e


# =====================================================
# 🧠 Session Factory
# =====================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# =====================================================
# 📚 Declarative Base
# =====================================================

Base = declarative_base()


# =====================================================
# 🔌 FastAPI Dependency
# =====================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =====================================================
# 🏥 Database Health Check
# =====================================================

def check_database_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


# =====================================================
# 🛠️ DEV Utility: Drop & Recreate All Tables (Safe)
# =====================================================

def reset_database_schema():
    """
    ⚠ DEV ONLY
    Drops all tables and recreates schema.
    Never use in production.
    """
    if ENVIRONMENT == "production":
        raise RuntimeError("🚨 Cannot reset schema in production!")

    print("🧨 Dropping all tables...")
    Base.metadata.drop_all(bind=engine)

    print("📦 Recreating all tables...")
    Base.metadata.create_all(bind=engine)

    print("✅ Database schema reset complete.")