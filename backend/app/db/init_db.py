from app.db.session import Base, engine
from app import models  # noqa: F401


def init_db() -> None:
    """Create database tables."""
    Base.metadata.create_all(bind=engine)
