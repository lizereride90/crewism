import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

log = logging.getLogger("crewism.db")

engine = None
_session_factory = None


class _SessionProxy:
    """Forwards calls to the current session factory so `from ... import SessionLocal` stays valid."""

    def __call__(self, *a, **k):
        get_engine()
        return _session_factory(*a, **k)

    def __repr__(self):
        return f"<SessionProxy factory={_session_factory}>"


SessionLocal = _SessionProxy()


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///crewism.db")
    return url


def get_engine():
    global engine, _session_factory
    if engine is None:
        url = _db_url()
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        engine = create_async_engine(url, echo=False, connect_args=connect_args)
        _session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine


def get_session_factory():
    get_engine()
    return _session_factory


def reset_engine():
    """Recreate engine (used by tests that change DATABASE_URL)."""
    global engine, _session_factory
    engine = None
    _session_factory = None
    return get_engine()


async def init_db():
    from . import models  # noqa: F401  ensure models registered

    eng = get_engine()
    # ensure directories exist for sqlite file
    url = _db_url()
    if url.startswith("sqlite"):
        path = url.split("///")[-1].split("?")[0]
        d = os.path.dirname(os.path.abspath(path))
        os.makedirs(d, exist_ok=True)
    async with eng.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
        if url.startswith("sqlite"):
            await conn.execute(models.text("PRAGMA journal_mode=WAL"))
            await conn.execute(models.text("PRAGMA foreign_keys=ON"))
    log.info("database ready")
