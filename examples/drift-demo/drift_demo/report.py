"""Compare demo scenarios with the root cause Agent Lens recorded."""

from __future__ import annotations

import json
import time
import urllib.error
from collections import Counter

from .client import RateLimited, request_json
from .identity import AGENT_NAME, DASHBOARD_FILTER, ENVIRONMENT
from .prompts import EXPECTED_ROOT_CAUSE
from .traffic import runs_path

# The API allows 600 requests a minute. A full pass over the default 60 traces,
# spaced by this gap, stays near 300 a minute even while every trace is still pending.
POLL_GAP_SECONDS = 0.2

TERMINAL_STATUSES = {
    "complete",
    "structural_only",
    "not_sampled",
    "insufficient_baseline",
    "embedding_unavailable",
    "invalid_input",
}


def load_runs() -> list[dict[str, str]]:
    path = runs_path()
    if not path.is_file():
        raise SystemExit(f"No demo runs at {path}. Send traffic first.")
    rows: list[dict[str, str]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append({str(key): str(value) for key, value in payload.items()})
    if not rows:
        raise SystemExit(f"Demo run log {path} is empty.")
    return rows


def collect_scores(
    api_url: str,
    runs: list[dict[str, str]],
    *,
    deadline: float,
) -> list[dict[str, object]]:
    pending = {run["trace_id"]: run for run in runs}
    found: dict[str, dict[str, object]] = {}
    end = time.monotonic() + deadline
    while pending and time.monotonic() < end:
        limited = False
        for trace_id in list(pending):
            if time.monotonic() >= end:
                break
            try:
                score = _latest_score(api_url, trace_id)
            except RateLimited as exc:
                _sleep_until(end, exc.retry_after)
                limited = True
                break
            if score is not None and str(score.get("status", "")) in TERMINAL_STATUSES:
                found[trace_id] = score
                pending.pop(trace_id)
            if pending:
                _sleep_until(end, POLL_GAP_SECONDS)
        if pending and not limited:
            _sleep_until(end, 1)
    rows: list[dict[str, object]] = []
    for run in runs:
        score = found.get(run["trace_id"])
        rows.append({**run, "score": score})
    return rows


def render(api_url: str, dashboard_url: str, rows: list[dict[str, object]]) -> str:
    findings = _finding_ids(api_url)
    lines = [
        f"Demo agent: {AGENT_NAME}",
        f"Demo environment: {ENVIRONMENT}",
        f"Walkthrough: {dashboard_url.rstrip('/')}{DASHBOARD_FILTER}",
        "",
        _table(rows, findings),
        "",
        _summary(rows),
    ]
    unavailable = [row for row in rows if _status(row.get("score")) == "embedding_unavailable"]
    if unavailable:
        lines.extend(
            [
                "",
                "Semantic scores are embedding_unavailable. Set OPENAI_API_KEY and "
                "re-run bootstrap so Mahalanobis distance and ambiguity are computed. "
                "Tool-failure and high-volatility findings still appear without it.",
            ]
        )
    missing = [row for row in rows if row.get("score") is None]
    if missing:
        lines.extend(
            [
                "",
                f"{len(missing)} traces were not scored before the deadline. "
                "Check that the Compose stack is up and the edge collector is reachable.",
            ]
        )
    return "\n".join(lines)


def report(*, api_url: str, dashboard_url: str, deadline: float) -> str:
    runs = load_runs()
    rows = collect_scores(api_url, runs, deadline=deadline)
    text = render(api_url, dashboard_url, rows)
    print(text)
    return text


def _latest_score(api_url: str, trace_id: str) -> dict[str, object] | None:
    try:
        result = request_json(f"{api_url.rstrip('/')}/v1/executions/{trace_id}/scores")
    except RuntimeError as exc:
        if "HTTP 404" in str(exc):
            return None
        raise
    if not isinstance(result, list) or not result:
        return None
    scores = [item for item in result if isinstance(item, dict)]
    complete = [item for item in scores if item.get("status") == "complete"]
    chosen = complete[-1] if complete else scores[-1]
    return chosen


def _finding_ids(api_url: str) -> set[str]:
    try:
        result = request_json(f"{api_url.rstrip('/')}/v1/findings?limit=200")
    except (RuntimeError, urllib.error.URLError, TimeoutError):
        return set()
    if not isinstance(result, list):
        return set()
    return {
        str(item["trace_id"])
        for item in result
        if isinstance(item, dict) and item.get("trace_id")
    }


def _table(rows: list[dict[str, object]], findings: set[str]) -> str:
    header = (
        f"{'scenario':<22} {'expected':<24} {'actual':<24} {'match':<6} "
        f"{'distance':>10} {'ambiguity':>10} {'volatility':>10}  trace"
    )
    body = [header]
    for row in rows:
        score = row.get("score")
        expected = EXPECTED_ROOT_CAUSE[str(row["scenario"])]
        actual = "pending"
        distance = ambiguity = volatility = "-"
        if isinstance(score, dict):
            actual = str(score.get("root_cause") or score.get("status"))
            distance = _metric(score.get("mahalanobis_distance"))
            ambiguity = _metric(score.get("ambiguity_score"))
            volatility = _metric(score.get("trajectory_volatility"))
        matched = "yes" if actual == expected else "no"
        finding = " finding" if str(row["trace_id"]) in findings else ""
        body.append(
            f"{row['scenario']!s:<22} {expected:<24} {actual:<24} {matched:<6} "
            f"{distance:>10} {ambiguity:>10} {volatility:>10}  {row['trace_id']}{finding}"
        )
    return "\n".join(body)


def _summary(rows: list[dict[str, object]]) -> str:
    counts: Counter[tuple[str, str]] = Counter()
    for row in rows:
        expected = EXPECTED_ROOT_CAUSE[str(row["scenario"])]
        score = row.get("score")
        actual = "pending"
        if isinstance(score, dict):
            actual = str(score.get("root_cause") or score.get("status"))
        counts[(expected, actual)] += 1
    lines = ["Expected vs actual:"]
    for (expected, actual), count in sorted(counts.items()):
        lines.append(f"  {expected} -> {actual}: {count}")
    return "\n".join(lines)


def _sleep_until(deadline: float, seconds: float) -> None:
    remaining = deadline - time.monotonic()
    if remaining <= 0 or seconds <= 0:
        return
    time.sleep(min(seconds, remaining))


def _status(score: object) -> str | None:
    if not isinstance(score, dict):
        return None
    status = score.get("status")
    if isinstance(status, str):
        return status
    return None


def _metric(value: object) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{float(value):.3f}"
    return "-"
