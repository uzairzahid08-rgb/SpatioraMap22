from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_DIR = BASE_DIR / "database"

DATABASE_DIR.mkdir(
    exist_ok=True
)

DATABASE_FILE = DATABASE_DIR / "geoasset.db"

DATABASE_URL = f"sqlite:///{DATABASE_FILE}"


engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False
    }
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)