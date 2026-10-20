import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Asegurar que el directorio de la base de datos SQLite exista
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:////"):
    db_file = db_url.replace("sqlite:////", "/")
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
elif db_url.startswith("sqlite:///"):
    db_file = db_url.replace("sqlite:///", "")
    parent_dir = os.path.dirname(db_file)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
