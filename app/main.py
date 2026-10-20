from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.games import router as games_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.models.game import Game
from app.persistence.database import Base, SessionLocal, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar tablas en SQLite
    Base.metadata.create_all(bind=engine)

    # Cargar datos semilla si la base de datos esta vacia
    db = SessionLocal()
    try:
        if db.query(Game).count() == 0:
            initial_games = [
                Game(
                    title="The Legend of Zelda: Tears of the Kingdom",
                    genre="Aventura / Mundo Abierto",
                    platform="Nintendo Switch",
                    release_year=2023,
                ),
                Game(
                    title="Cyberpunk 2077: Phantom Liberty",
                    genre="RPG / Accion",
                    platform="PC / PS5 / Xbox Series",
                    release_year=2023,
                ),
                Game(
                    title="Elden Ring",
                    genre="Soulslike / Accion RPG",
                    platform="Multiplataforma",
                    release_year=2022,
                ),
            ]
            db.add_all(initial_games)
            db.commit()
    finally:
        db.close()

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend de gestion de videojuegos con proteccion Bearer Token para practica de Ciberseguridad",
    lifespan=lifespan,
)

# Configuracion de CORS estricto para el frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health_router)
app.include_router(games_router, prefix=settings.API_PREFIX)
