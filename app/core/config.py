import os
from pydantic import BaseModel


class Settings(BaseModel):
    PROJECT_NAME: str = "Videojuegos API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = [
        "http://localhost:4200",
    ]
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:////data/games.db")


settings = Settings()
