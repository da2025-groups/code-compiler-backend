from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.question import Question
from app.models.submission import Submission
from app.services import piston_service


async def run_against_sample(
    question_id: int,
    language: str,
    code: str,
    db: Session,
    *,
    client=None,
) -> dict:
    """Run code against the question's sample_input only. No DB write."""
    q = db.get(Question, question_id)
    if q is None or not q.is_published:
        raise HTTPException(status_code=404, detail="Question not found")
    stdin = q.sample_input or ""
    return await piston_service.run_code(language, code, stdin=stdin, client=client)


async def judge_submission(
    question_id: int,
    language: str,
    code: str,
    user_id: int,
    db: Session,
    *,
    client=None,
) -> dict:
    """Run code against all test_cases, score, persist Submission, return SubmitResponse dict."""
    q = db.get(Question, question_id)
    if q is None or not q.is_published:
        raise HTTPException(status_code=404, detail="Question not found")

    test_cases = q.test_cases or []
    if not test_cases:
        raise HTTPException(status_code=422, detail="Question has no test cases")

    results = []
    passed = 0
    max_time_ms = 0

    for case in test_cases:
        stdin = case.get("input", "")
        expected = case.get("expected_output", case.get("output", ""))
        result = await piston_service.run_code(language, code, stdin=stdin, client=client)
        actual = result["stdout"]
        verdict = (
            "pass"
            if result["status"] == "accepted" and actual.strip() == expected.strip()
            else "fail"
        )
        if verdict == "pass":
            passed += 1
        max_time_ms = max(max_time_ms, result["execution_time_ms"])
        results.append({
            "input": stdin,
            "expected": expected,
            "actual": actual,
            "verdict": verdict,
        })

    total = len(test_cases)
    score = (passed / total) * 100.0 if total > 0 else 0.0
    status = "accepted" if score == 100.0 else "wrong_answer"

    sub = Submission(
        user_id=user_id,
        question_id=question_id,
        language=language,
        code=code,
        status=status,
        passed_cases=passed,
        total_cases=total,
        score=score,
        execution_time_ms=max_time_ms,
    )
    db.add(sub)
    db.commit()

    return {
        "status": status,
        "score": score,
        "passed_cases": passed,
        "total_cases": total,
        "results": results,
    }


def get_my_submissions(user_id: int, db: Session) -> list[dict]:
    """Return authenticated user's submission history with question titles."""
    subs = (
        db.query(Submission)
        .filter(Submission.user_id == user_id)
        .order_by(Submission.id.desc())
        .all()
    )
    q_ids = list({s.question_id for s in subs})
    titles = {
        q.id: q.title
        for q in db.query(Question).filter(Question.id.in_(q_ids)).all()
    }
    return [
        {
            "id": s.id,
            "question_id": s.question_id,
            "question_title": titles.get(s.question_id, ""),
            "language": s.language,
            "status": s.status,
            "score": s.score,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else "",
        }
        for s in subs
    ]


def get_all_submissions(db: Session) -> list[dict]:
    """Return all submissions with user names and question titles (admin view)."""
    from app.models.user import User

    subs = db.query(Submission).order_by(Submission.id.desc()).all()
    u_ids = list({s.user_id for s in subs})
    q_ids = list({s.question_id for s in subs})
    users = {u.id: u.name for u in db.query(User).filter(User.id.in_(u_ids)).all()}
    titles = {
        q.id: q.title
        for q in db.query(Question).filter(Question.id.in_(q_ids)).all()
    }
    return [
        {
            "id": s.id,
            "user_name": users.get(s.user_id, ""),
            "question_title": titles.get(s.question_id, ""),
            "language": s.language,
            "status": s.status,
            "score": s.score,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else "",
        }
        for s in subs
    ]
