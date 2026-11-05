"""Database engine/session and tenant-scoped query helper.

Tenant isolation has two walls:
1. Application: every query goes through `scoped()`, which always filters on tenant_id.
2. Postgres: row-level security policies keyed on the `app.tenant_id` setting
   (see migrations/postgres_rls.sql). `set_tenant()` sets it per transaction.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import TypeVar

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal: sessionmaker | None = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = get_settings().database_url
        kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        _engine = create_engine(url, pool_pre_ping=True, **kwargs)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def reset_engine() -> None:
    """Used by tests to point at a fresh database."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(get_engine())


def get_session() -> Iterator[Session]:
    get_engine()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def session_scope() -> Session:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


def set_tenant(session: Session, tenant_id: int) -> None:
    """Activate Postgres RLS for this transaction. No-op on SQLite."""
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(int(tenant_id))})


M = TypeVar("M")


def scoped(model: type[M], tenant_id: int):
    """SELECT for `model` restricted to one tenant. Use this instead of select()."""
    return select(model).where(model.tenant_id == tenant_id)  # type: ignore[attr-defined]


def get_scoped(session: Session, model: type[M], tenant_id: int, obj_id: int) -> M | None:
    """Fetch one row by id ONLY if it belongs to the tenant. Cross-tenant ids look like 404s."""
    return session.scalars(scoped(model, tenant_id).where(model.id == obj_id)).first()  # type: ignore[attr-defined]


def utcnow() -> datetime:
    """Naive UTC timestamp (stored consistently across SQLite and Postgres)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
