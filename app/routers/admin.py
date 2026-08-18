from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_admin
from app.schemas.question import QuestionCreate, QuestionUpdate
from app.services import question_service

router = APIRouter()


@router.get("/questions")
def admin_list_questions(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """List all questions including unpublished ones."""
    return question_service.list_all_questions(db)


@router.post("/questions", status_code=201)
def admin_create_question(
    req: QuestionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Create a new question. test_cases stored but never exposed to students."""
    return question_service.create_question(db, req, created_by=current_user.id)


@router.put("/questions/{question_id}")
def admin_update_question(
    question_id: int,
    req: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Update an existing question. Returns 404 if not found."""
    result = question_service.update_question(db, question_id, req)
    if result is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return result


@router.get("/submissions")
def admin_submissions(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Return all submissions with user name and question title."""
    from app.services import judge_service
    return judge_service.get_all_submissions(db)
