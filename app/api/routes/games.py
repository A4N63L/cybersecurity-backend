from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.security import verify_bearer_format
from app.persistence.database import get_db
from app.schemas.game import GameCreate, GameResponse
from app.services.game_service import game_service

router = APIRouter(prefix="/games", tags=["Videojuegos"])


@router.get("", response_model=list[GameResponse])
def get_games(
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bearer_format),
):
    """Retorna el catalogo de videojuegos.

    Requiere encabezado 'Authorization: Bearer <token>' con formato sintactico valido.
    """
    return game_service.list_games(db)


@router.post("", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
def create_game(
    game_in: GameCreate,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bearer_format),
):
    """Registra un nuevo videojuego en el sistema.

    Requiere encabezado 'Authorization: Bearer <token>' con formato sintactico valido.
    """
    return game_service.register_game(db, game_in)
