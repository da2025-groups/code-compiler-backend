from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.question import Question
from app.models.submission import Submission
from app.schemas.question import QuestionCreate, QuestionUpdate

_VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def _dt(dt) -> str:
    return dt.isoformat() if dt else ""


def _assert_difficulty(difficulty: str) -> None:
    if difficulty not in _VALID_DIFFICULTIES:
        raise HTTPException(status_code=422, detail="difficulty must be easy, medium, or hard")


def list_published_questions(db: Session, user_id: int | None = None) -> list[dict]:
    questions = db.query(Question).filter(Question.is_published == True).all()
    solved_ids: set[int] = set()
    if user_id is not None:
        solved_ids = {
            s.question_id
            for s in db.query(Submission).filter(
                Submission.user_id == user_id,
                Submission.status == "accepted",
            ).all()
        }
    return [
        {
            "id": q.id,
            "title": q.title,
            "difficulty": q.difficulty,
            "is_solved": q.id in solved_ids,
            "created_at": _dt(q.created_at),
        }
        for q in questions
    ]


def get_published_question(db: Session, question_id: int) -> dict | None:
    q = db.query(Question).filter(
        Question.id == question_id, Question.is_published == True
    ).first()
    if q is None:
        return None
    return {
        "id": q.id,
        "title": q.title,
        "description": q.description,
        "difficulty": q.difficulty,
        "constraints": q.constraints,
        "sample_input": q.sample_input,
        "sample_output": q.sample_output,
        "created_at": _dt(q.created_at),
    }


def create_question(db: Session, req: QuestionCreate, created_by: int) -> dict:
    _assert_difficulty(req.difficulty)
    q = Question(
        title=req.title,
        description=req.description,
        difficulty=req.difficulty,
        constraints=req.constraints,
        sample_input=req.sample_input,
        sample_output=req.sample_output,
        test_cases=req.test_cases,
        is_published=req.is_published,
        created_by=created_by,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return {
        "id": q.id,
        "title": q.title,
        "difficulty": q.difficulty,
        "is_published": q.is_published,
        "created_at": _dt(q.created_at),
        "updated_at": _dt(q.updated_at),
    }


def update_question(db: Session, question_id: int, req: QuestionUpdate) -> dict | None:
    _assert_difficulty(req.difficulty)
    q = db.get(Question, question_id)
    if q is None:
        return None
    for key, val in req.model_dump(exclude_unset=False).items():
        setattr(q, key, val)
    db.commit()
    db.refresh(q)
    return {
        "id": q.id,
        "title": q.title,
        "difficulty": q.difficulty,
        "is_published": q.is_published,
        "created_at": _dt(q.created_at),
        "updated_at": _dt(q.updated_at),
    }


def list_all_questions(db: Session) -> list[dict]:
    questions = db.query(Question).order_by(Question.id).all()
    return [
        {
            "id": q.id,
            "title": q.title,
            "difficulty": q.difficulty,
            "is_published": q.is_published,
            "created_at": _dt(q.created_at),
            "updated_at": _dt(q.updated_at),
        }
        for q in questions
    ]
