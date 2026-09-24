from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import os


# ---------------------------------------------------------
# Project base directory
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------
# Database location
# ---------------------------------------------------------
# Local computer:
#     E:\New folder (4)\GeoAssetManager\database\geoasset.db
#
# Vercel:
#     /tmp/geoasset.db
#
# Vercel's deployed project directory is read-only.
# /tmp is the writable temporary directory available
# during a serverless function execution.
# ---------------------------------------------------------

if os.environ.get("VERCEL"):
    DATABASE_FILE = Path("/tmp/geoasset.db")
else:
    DATABASE_DIR = BASE_DIR / "database"

    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    DATABASE_FILE = DATABASE_DIR / "geoasset.db"


# ---------------------------------------------------------
# SQLAlchemy database URL
# ---------------------------------------------------------

DATABASE_URL = f"sqlite:///{DATABASE_FILE}"


# ---------------------------------------------------------
# SQLAlchemy engine
# ---------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False
    }
)


# ---------------------------------------------------------
# Database session
# ---------------------------------------------------------

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)