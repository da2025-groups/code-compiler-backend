from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.services import ranking_service

router = APIRouter()


@router.get("")
def global_rankings(db: Session = Depends(get_db)):
    """Public global leaderboard ordered by total_score desc, solved_count desc."""
    return ranking_service.get_global_rankings(db)


@router.get("/{question_id}")
def question_rankings(question_id: int, db: Session = Depends(get_db)):
    """Public per-question leaderboard ordered by best_score desc, execution_time_ms asc."""
    return ranking_service.get_question_rankings(db, question_id)
