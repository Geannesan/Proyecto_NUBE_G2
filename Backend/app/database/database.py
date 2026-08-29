import os
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    sessionmaker,
)


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./deepfakeshield.db",
)


connect_args: dict[str, object] = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Este import registra Analysis en Base.metadata.
    from app.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Migración mínima compatible con bases creadas por la versión 2.
    columns = {column["name"] for column in inspect(engine).get_columns("analyses")}
    if "analysis_metadata" not in columns:
        json_type = "JSONB" if engine.dialect.name == "postgresql" else "JSON"
        with engine.begin() as connection:
            connection.execute(text(
                f"ALTER TABLE analyses ADD COLUMN analysis_metadata {json_type} NOT NULL DEFAULT '{{}}'"
            ))
