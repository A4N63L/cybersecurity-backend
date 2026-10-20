from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String
from app.persistence.database import Base


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(150), nullable=False, index=True)
    genre = Column(String(80), nullable=False)
    platform = Column(String(80), nullable=False)
    release_year = Column(Integer, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
