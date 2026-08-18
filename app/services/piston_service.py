import time
import httpx
from fastapi import HTTPException
import app.config as _config

_TIMEOUT = 30.0
_RUN_TIMEOUT_MS = 5_000
_COMPILE_TIMEOUT_MS = 10_000
_MEMORY_LIMIT_BYTES = 128 * 1024 * 1024  # 128 MB

# Piston language name as registered in its runtime index
LANGUAGE_ALIASES: dict[str, str] = {
    "python3":     "python",
    "py":          "python",
    "js":          "javascript",
    "node":        "javascript",
    "nodejs":      "javascript",
    "cpp":         "gcc",
    "c++":         "gcc",
    "c_plus_plus": "gcc",
    "c":           "gcc",
}

# Languages that need extra wall-time (e.g. JVM startup overhead)
_LANGUAGE_RUN_TIMEOUT_MS: dict[str, int] = {
    "java":   10_000,
    "kotlin": 10_000,
    "scala":  10_000,
    "groovy": 10_000,
    "gcc":     8_000,
    "rust":    8_000,
}


async def execute_code(
    language: str,
    version: str,
    code: str,
    stdin: str = "",
    *,
    client: httpx.AsyncClient | None = None,
) -> dict:
    """POST /api/v2/execute and return the full Piston response dict.

    Pass ``client`` in tests to inject a mock; production callers leave it None.
    Raises HTTPException(422) when the language/version is not installed.
    """
    url = f"{_config.settings.piston_url}/api/v2/execute"
    run_timeout = _LANGUAGE_RUN_TIMEOUT_MS.get(language, _RUN_TIMEOUT_MS)
    # gcc runtime uses the file extension to pick gcc vs g++.
    # Without a name Piston defaults to "file0.code.c" → compiled as C (no iostream).
    # Force .cpp so Piston invokes g++ for all C++ submissions.
    file_entry: dict = {"content": code}
    if language == "gcc":
        file_entry["name"] = "main.cpp"
    payload = {
        "language": language,
        "version": version,
        "files": [file_entry],
        "stdin": stdin,
        "run_timeout": run_timeout,
        "compile_timeout": _COMPILE_TIMEOUT_MS,
        "memory_limit": _MEMORY_LIMIT_BYTES,
    }
    if client is not None:
        resp = await client.post(url, json=payload)
    else:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            resp = await c.post(url, json=payload)
    if resp.status_code == 400:
        detail = resp.json().get("message", "Unknown language or version")
        raise HTTPException(status_code=422, detail=detail)
    resp.raise_for_status()
    return resp.json()


def _normalize_result(piston_resp: dict, elapsed_ms: int) -> dict:
    """Map a raw Piston response to a normalised ExecutionResult dict."""
    compile_info = piston_resp.get("compile")
    run_info = piston_resp.get("run", {})

    if compile_info and compile_info.get("code", 0) != 0:
        return {
            "stdout": run_info.get("stdout", ""),
            "stderr": compile_info.get("stderr", ""),
            "execution_time_ms": elapsed_ms,
            "status": "runtime_error",
        }
    if run_info.get("signal") == "SIGKILL":
        status = "time_limit_exceeded"
    elif run_info.get("code", 0) != 0:
        status = "runtime_error"
    else:
        status = "accepted"
    return {
        "stdout": run_info.get("stdout", ""),
        "stderr": run_info.get("stderr", ""),
        "execution_time_ms": elapsed_ms,
        "status": status,
    }


async def run_code(
    language: str,
    code: str,
    stdin: str = "",
    *,
    client: httpx.AsyncClient | None = None,
) -> dict:
    """Execute code and return a normalised ExecutionResult-shaped dict.

    Resolves language aliases (e.g. python3 -> python, cpp -> c++), delegates
    to execute_code, measures wall-clock time, and normalises the Piston
    response into {stdout, stderr, execution_time_ms, status}.
    """
    resolved = LANGUAGE_ALIASES.get(language.lower(), language.lower())
    t0 = time.perf_counter()
    piston_resp = await execute_code(resolved, "*", code, stdin, client=client)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return _normalize_result(piston_resp, elapsed_ms)


async def get_runtimes(
    *, client: httpx.AsyncClient | None = None
) -> list:
    """GET /api/v2/runtimes and return the list of runtime dicts.

    Pass ``client`` in tests to inject a mock; production callers leave it None.
    """
    url = f"{_config.settings.piston_url}/api/v2/runtimes"
    if client is not None:
        resp = await client.get(url)
    else:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            resp = await c.get(url)
    resp.raise_for_status()
    return resp.json()
