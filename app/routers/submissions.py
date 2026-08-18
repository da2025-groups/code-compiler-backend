from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user
from app.schemas.submission import RunRequest, SubmitRequest
from app.services import judge_service

router = APIRouter()


@router.post("/run")
async def submission_run(
    req: RunRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Run code against the question's sample input only. No submission persisted."""
    return await judge_service.run_against_sample(
        req.question_id, req.language, req.code, db
    )


@router.post("/submit")
async def submission_submit(
    req: SubmitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Run code against all test cases, judge, persist and return SubmitResponse."""
    return await judge_service.judge_submission(
        req.question_id, req.language, req.code, current_user.id, db
    )


@router.get("/my")
def my_submissions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return the authenticated user's submission history."""
    return judge_service.get_my_submissions(current_user.id, db)
