import httpx
import app.config as _config

_TIMEOUT = 15.0
_RUN_TIMEOUT_MS = 10_000


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
    """
    url = f"{_config.settings.piston_url}/api/v2/execute"
    payload = {
        "language": language,
        "version": version,
        "files": [{"content": code}],
        "stdin": stdin,
        "run_timeout": _RUN_TIMEOUT_MS,
    }
    if client is not None:
        resp = await client.post(url, json=payload)
    else:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            resp = await c.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()


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
