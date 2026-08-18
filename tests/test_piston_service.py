import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock


# ── helpers ───────────────────────────────────────────────────────────────────

def _mock_response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ── execute_code ──────────────────────────────────────────────────────────────

async def test_execute_code_sends_correct_payload():
    """execute_code POSTs language/version/files/stdin to /api/v2/execute."""
    from app.services.piston_service import execute_code

    client = AsyncMock()
    client.post.return_value = _mock_response({
        "language": "python", "version": "3.10.0",
        "run": {"stdout": "hello\n", "stderr": "", "code": 0, "signal": None},
    })

    result = await execute_code("python", "*", "print('hello')", client=client)

    client.post.assert_called_once()
    _, kwargs = client.post.call_args
    body = kwargs["json"]
    assert body["language"] == "python"
    assert body["version"] == "*"
    assert body["files"][0]["content"] == "print('hello')"
    assert body["stdin"] == ""
    assert result["run"]["stdout"] == "hello\n"


async def test_execute_code_includes_stdin():
    """execute_code passes stdin through to Piston payload."""
    from app.services.piston_service import execute_code

    client = AsyncMock()
    client.post.return_value = _mock_response({"run": {"stdout": "42\n", "code": 0}})

    await execute_code("python", "*", "print(input())", stdin="42", client=client)

    _, kwargs = client.post.call_args
    assert kwargs["json"]["stdin"] == "42"


async def test_execute_code_raises_on_piston_error():
    """execute_code propagates HTTPStatusError on non-200 response."""
    from app.services.piston_service import execute_code

    client = AsyncMock()
    client.post.return_value = _mock_response({}, status_code=500)

    with pytest.raises(httpx.HTTPStatusError):
        await execute_code("python", "*", "print('hello')", client=client)


# ── get_runtimes ──────────────────────────────────────────────────────────────

async def test_get_runtimes_returns_list():
    """get_runtimes GETs /api/v2/runtimes and returns list of runtime dicts."""
    from app.services.piston_service import get_runtimes

    client = AsyncMock()
    client.get.return_value = _mock_response([
        {"language": "python", "version": "3.10.0"},
        {"language": "javascript", "version": "18.15.0"},
    ])

    runtimes = await get_runtimes(client=client)

    client.get.assert_called_once()
    assert isinstance(runtimes, list)
    assert runtimes[0]["language"] == "python"


async def test_get_runtimes_raises_on_error():
    """get_runtimes propagates HTTPStatusError on non-200 response."""
    from app.services.piston_service import get_runtimes

    client = AsyncMock()
    client.get.return_value = _mock_response({}, status_code=503)

    with pytest.raises(httpx.HTTPStatusError):
        await get_runtimes(client=client)
