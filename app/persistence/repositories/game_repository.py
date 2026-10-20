from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.models.game import Game
from app.schemas.game import GameCreate


class GameRepository:
    def get_all(self, db: Session, skip: int = 0, limit: int = 200) -> list[Game]:
        return (
            db.query(Game)
            .order_by(desc(Game.id))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, db: Session, game_in: GameCreate) -> Game:
        db_game = Game(
            title=game_in.title.strip(),
            genre=game_in.genre.strip(),
            platform=game_in.platform.strip(),
            release_year=game_in.release_year,
        )
        db.add(db_game)
        db.commit()
        db.refresh(db_game)
        return db_game

    def count(self, db: Session) -> int:
        return db.query(Game).count()


game_repository = GameRepository()
