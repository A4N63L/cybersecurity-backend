from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class GameBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(..., min_length=1, max_length=150, description="Titulo del videojuego")
    genre: str = Field(..., min_length=1, max_length=80, description="Genero (ej. RPG, Accion)")
    platform: str = Field(..., min_length=1, max_length=80, description="Plataforma (ej. PC, Switch, PS5)")
    release_year: int = Field(..., ge=1950, le=2100, description="Ano de lanzamiento")


class GameCreate(GameBase):
    pass


class GameResponse(GameBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
