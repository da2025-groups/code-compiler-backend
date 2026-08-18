from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_optional_user
from app.services import question_service

router = APIRouter()


@router.get("")
def list_questions(
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    """Return all published questions. is_solved reflects authenticated user's submissions."""
    user_id = current_user.id if current_user else None
    return question_service.list_published_questions(db, user_id=user_id)


@router.get("/{question_id}")
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    """Return a single published question. test_cases are never included."""
    result = question_service.get_published_question(db, question_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return result
