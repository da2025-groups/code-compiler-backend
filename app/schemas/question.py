from typing import Any
from pydantic import BaseModel


class QuestionCreate(BaseModel):
    title: str
    description: str
    difficulty: str  # easy|medium|hard
    constraints: str | None = None
    sample_input: str | None = None
    sample_output: str | None = None
    test_cases: list[Any] | None = None
    is_published: bool = False


class QuestionUpdate(QuestionCreate):
    pass


class QuestionListItem(BaseModel):
    id: int
    title: str
    difficulty: str
    is_solved: bool = False
    created_at: str

    model_config = {"from_attributes": True}


class QuestionDetail(BaseModel):
    id: int
    title: str
    description: str
    difficulty: str
    constraints: str | None = None
    sample_input: str | None = None
    sample_output: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class AdminQuestionItem(BaseModel):
    id: int
    title: str
    difficulty: str
    is_published: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
