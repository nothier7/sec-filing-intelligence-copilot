from collections.abc import Generator
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from sec_copilot.config import get_settings


def create_db_engine(database_url: Optional[str] = None) -> Engine:
    url = database_url or get_settings().database_url
    return create_engine(url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


engine = create_db_engine()
SessionLocal = create_session_factory(engine)


@contextmanager
def session_scope(session_factory: sessionmaker[Session] = SessionLocal) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
