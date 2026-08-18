from pydantic import BaseModel


class GlobalRankingItem(BaseModel):
    rank: int
    user_id: int
    name: str
    solved_count: int
    total_score: float


class QuestionRankingItem(BaseModel):
    rank: int
    user_id: int
    name: str
    best_score: float
    execution_time_ms: int
