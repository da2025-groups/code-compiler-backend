from typing import Any
from pydantic import BaseModel


class RunRequest(BaseModel):
    question_id: int
    language: str
    code: str


class SubmitRequest(BaseModel):
    question_id: int
    language: str
    code: str


class PlaygroundRunRequest(BaseModel):
    language: str
    code: str
    stdin: str = ""


class ExecutionResult(BaseModel):
    stdout: str
    stderr: str
    execution_time_ms: int
    status: str  # accepted|runtime_error|time_limit_exceeded


class CaseVerdict(BaseModel):
    input: str
    expected: str
    actual: str
    verdict: str  # pass|fail


class SubmitResponse(BaseModel):
    status: str
    score: float
    passed_cases: int
    total_cases: int
    results: list[CaseVerdict]


class MySubmissionItem(BaseModel):
    id: int
    question_id: int
    question_title: str
    language: str
    status: str
    score: float
    submitted_at: str

    model_config = {"from_attributes": True}


class AdminSubmissionItem(BaseModel):
    id: int
    user_name: str
    question_title: str
    language: str
    status: str
    score: float
    submitted_at: str
