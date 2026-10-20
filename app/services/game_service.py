from sqlalchemy.orm import Session
from app.models.game import Game
from app.persistence.repositories.game_repository import game_repository
from app.schemas.game import GameCreate


class GameService:
    def list_games(self, db: Session, skip: int = 0, limit: int = 200) -> list[Game]:
        return game_repository.get_all(db, skip=skip, limit=limit)

    def register_game(self, db: Session, game_in: GameCreate) -> Game:
        # Aqui podrian agregarse validaciones de negocio especificas
        return game_repository.create(db, game_in)

    def total_games(self, db: Session) -> int:
        return game_repository.count(db)


game_service = GameService()
