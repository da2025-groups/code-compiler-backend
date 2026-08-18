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


# ── D2: language aliases + enhanced payload ───────────────────────────────────

def test_language_aliases_map_known_names():
    """LANGUAGE_ALIASES maps common shorthand to Piston runtime names."""
    from app.services.piston_service import LANGUAGE_ALIASES
    assert LANGUAGE_ALIASES["python3"] == "python"
    assert LANGUAGE_ALIASES["js"] == "javascript"
    assert LANGUAGE_ALIASES["cpp"] == "c++"


async def test_execute_code_includes_memory_limit():
    """execute_code sends memory_limit in the Piston payload."""
    from app.services.piston_service import execute_code

    client = AsyncMock()
    client.post.return_value = _mock_response({"run": {"stdout": "", "stderr": "", "code": 0}})
    await execute_code("python", "*", "", client=client)
    _, kwargs = client.post.call_args
    assert "memory_limit" in kwargs["json"]


async def test_execute_code_includes_compile_timeout():
    """execute_code sends compile_timeout in the Piston payload."""
    from app.services.piston_service import execute_code

    client = AsyncMock()
    client.post.return_value = _mock_response({"run": {"stdout": "", "stderr": "", "code": 0}})
    await execute_code("python", "*", "", client=client)
    _, kwargs = client.post.call_args
    assert "compile_timeout" in kwargs["json"]


# ── D3: run_code + status normalisation ──────────────────────────────────────

async def test_run_code_returns_accepted():
    """run_code returns status=accepted when exit code is 0 and no signal."""
    from app.services.piston_service import run_code

    client = AsyncMock()
    client.post.return_value = _mock_response({
        "run": {"stdout": "hello\n", "stderr": "", "code": 0, "signal": None}
    })
    result = await run_code("python", "print('hello')", client=client)
    assert result["status"] == "accepted"
    assert result["stdout"] == "hello\n"
    assert isinstance(result["execution_time_ms"], int)


async def test_run_code_returns_runtime_error():
    """run_code returns status=runtime_error when exit code is non-zero."""
    from app.services.piston_service import run_code

    client = AsyncMock()
    client.post.return_value = _mock_response({
        "run": {"stdout": "", "stderr": "NameError: x", "code": 1, "signal": None}
    })
    result = await run_code("python", "bad code", client=client)
    assert result["status"] == "runtime_error"
    assert result["stderr"] == "NameError: x"


async def test_run_code_returns_time_limit_exceeded():
    """run_code returns status=time_limit_exceeded when signal is SIGKILL."""
    from app.services.piston_service import run_code

    client = AsyncMock()
    client.post.return_value = _mock_response({
        "run": {"stdout": "", "stderr": "", "code": -1, "signal": "SIGKILL"}
    })
    result = await run_code("python", "while True: pass", client=client)
    assert result["status"] == "time_limit_exceeded"


async def test_run_code_compile_failure_returns_runtime_error():
    """run_code returns runtime_error and compile stderr when compile step fails."""
    from app.services.piston_service import run_code

    client = AsyncMock()
    client.post.return_value = _mock_response({
        "compile": {"stdout": "", "stderr": "error: undeclared identifier", "code": 1, "signal": None},
        "run": {"stdout": "", "stderr": "", "code": 0, "signal": None},
    })
    result = await run_code("c++", "bad code", client=client)
    assert result["status"] == "runtime_error"
    assert "undeclared" in result["stderr"]


async def test_run_code_resolves_language_alias():
    """run_code resolves alias before sending to Piston (python3 → python)."""
    from app.services.piston_service import run_code

    client = AsyncMock()
    client.post.return_value = _mock_response({
        "run": {"stdout": "", "stderr": "", "code": 0, "signal": None}
    })
    await run_code("python3", "pass", client=client)
    _, kwargs = client.post.call_args
    assert kwargs["json"]["language"] == "python"
