import enum
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from starfall.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _default_sql(column) -> str:
    if column.server_default is not None:
        return ""
    if column.default is not None and column.default.arg is not None:
        value = column.default.arg
        if callable(value):
            return ""
        if isinstance(value, enum.Enum):
            value = value.value
        if isinstance(value, bool):
            return f" DEFAULT {1 if value else 0}"
        if isinstance(value, (int, float)):
            return f" DEFAULT {value}"
        if isinstance(value, str):
            escaped = value.replace("'", "''")
            return f" DEFAULT '{escaped}'"
    if column.nullable:
        return " DEFAULT NULL"
    return ""


def migrate_sqlite_schema() -> None:
    """Add missing columns on existing SQLite tables (create_all does not alter tables)."""
    if not settings.database_url.startswith("sqlite"):
        return

    from starfall import models  # noqa: F401

    with engine.begin() as conn:
        inspector = inspect(conn)
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                default = _default_sql(column)
                stmt = f"ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}{default}"
                conn.execute(text(stmt))
                existing.add(column.name)


def init_db() -> None:
    from starfall import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema()
