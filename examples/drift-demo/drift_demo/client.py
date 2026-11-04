"""Small JSON client for the local Agent Lens API."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


class RateLimited(RuntimeError):
    """The API returned 429. `retry_after` is how long to wait before the next call."""

    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(f"HTTP 429; retry after {retry_after:.0f}s")


def request_json(url: str, *, method: str = "GET", body: object | None = None) -> object:
    payload = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url,
        method=method,
        data=payload,
        headers={"Content-Type": "application/json"} if payload else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            retry_after = _retry_after(exc)
            exc.read()
            raise RateLimited(retry_after) from exc
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {detail}") from exc


def _retry_after(exc: urllib.error.HTTPError) -> float:
    raw = exc.headers.get("Retry-After") if exc.headers else None
    try:
        parsed = float(raw) if raw else 60.0
    except ValueError:
        parsed = 60.0
    return max(1.0, parsed)


def wait_until_ready(api_url: str, deadline: float) -> None:
    end = time.monotonic() + deadline
    ready_url = f"{api_url.rstrip('/')}/health/ready"
    last_error: Exception | None = None
    while time.monotonic() < end:
        try:
            result = request_json(ready_url)
            if isinstance(result, dict) and result.get("status") == "ready":
                return
        except (TimeoutError, urllib.error.URLError, OSError, RuntimeError) as exc:
            last_error = exc
        time.sleep(1)
    detail = f": {last_error}" if last_error else ""
    raise TimeoutError(f"API not ready within {deadline:.0f}s{detail}")
