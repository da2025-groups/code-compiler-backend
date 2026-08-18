from sqlalchemy.orm import Session
from app.models.submission import Submission
from app.models.user import User


def get_global_rankings(db: Session) -> list[dict]:
    """Global leaderboard: total_score desc, solved_count desc."""
    subs = db.query(Submission).all()
    if not subs:
        return []

    # best score per (user_id, question_id)
    best: dict[tuple[int, int], float] = {}
    for s in subs:
        key = (s.user_id, s.question_id)
        if key not in best or s.score > best[key]:
            best[key] = s.score

    # aggregate per user
    user_stats: dict[int, dict] = {}
    for (user_id, _), score in best.items():
        if user_id not in user_stats:
            user_stats[user_id] = {"total_score": 0.0, "solved_count": 0}
        user_stats[user_id]["total_score"] += score
        if score == 100.0:
            user_stats[user_id]["solved_count"] += 1

    user_ids = list(user_stats.keys())
    names = {u.id: u.name for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    rows = sorted(
        user_stats.items(),
        key=lambda x: (-x[1]["total_score"], -x[1]["solved_count"]),
    )
    return [
        {
            "rank": i,
            "user_id": uid,
            "name": names.get(uid, ""),
            "solved_count": stats["solved_count"],
            "total_score": stats["total_score"],
        }
        for i, (uid, stats) in enumerate(rows, start=1)
    ]


def get_question_rankings(db: Session, question_id: int) -> list[dict]:
    """Per-question leaderboard: best_score desc, execution_time_ms asc."""
    subs = db.query(Submission).filter(Submission.question_id == question_id).all()
    if not subs:
        return []

    # best score + fastest time for that score per user
    best: dict[int, tuple[float, int]] = {}  # user_id -> (best_score, min_time)
    for s in subs:
        if s.user_id not in best:
            best[s.user_id] = (s.score, s.execution_time_ms)
        else:
            cur_score, cur_time = best[s.user_id]
            if s.score > cur_score or (
                s.score == cur_score and s.execution_time_ms < cur_time
            ):
                best[s.user_id] = (s.score, s.execution_time_ms)

    user_ids = list(best.keys())
    names = {u.id: u.name for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    rows = sorted(best.items(), key=lambda x: (-x[1][0], x[1][1]))
    return [
        {
            "rank": i,
            "user_id": uid,
            "name": names.get(uid, ""),
            "best_score": score,
            "execution_time_ms": time_ms,
        }
        for i, (uid, (score, time_ms)) in enumerate(rows, start=1)
    ]
