from fastapi import APIRouter
from app.schemas.submission import PlaygroundRunRequest, ExecutionResult
from app.services import piston_service

router = APIRouter()


@router.post("/run", response_model=ExecutionResult)
async def playground_run(req: PlaygroundRunRequest) -> ExecutionResult:
    """Execute arbitrary code in the Piston sandbox. No auth required."""
    result = await piston_service.run_code(req.language, req.code, stdin=req.stdin)
    return result
