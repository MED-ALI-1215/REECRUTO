from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session


class Base(DeclarativeBase):
    pass


def _get_engine():
    """Lazy engine — only created on first call, not at import time."""
    from app.core.config import get_settings
    settings = get_settings()
    url = settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


# Module-level references — resolved lazily on first use
class _LazyEngine:
    _engine = None

    def __getattr__(self, name):
        if self._engine is None:
            type(self)._engine = _get_engine()
        return getattr(self._engine, name)


engine = _LazyEngine()


def _get_session_factory():
    from app.core.config import get_settings
    settings = get_settings()
    url = settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    eng = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    return sessionmaker(autocommit=False, autoflush=False, bind=eng), eng


_session_factory = None
_bound_engine = None


def _get_factory():
    global _session_factory, _bound_engine
    if _session_factory is None:
        _session_factory, _bound_engine = _get_session_factory()
    return _session_factory, _bound_engine


def SessionLocal():
    factory, _ = _get_factory()
    return factory()


def get_db() -> Generator[Session, None, None]:
    factory, _ = _get_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    _, eng = _get_factory()
    Base.metadata.create_all(bind=eng)


def get_engine():
    _, eng = _get_factory()
    return eng
