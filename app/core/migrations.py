"""Лёгкие миграции SQLite без Alembic."""

from sqlalchemy import inspect, text

from app.core.database import engine


def ensure_trip_origin_column() -> None:
    inspector = inspect(engine)
    if "trip_requests" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("trip_requests")}
    if "origin" in columns:
        return
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE trip_requests ADD COLUMN origin VARCHAR(255) NOT NULL DEFAULT 'Москва'")
        )
