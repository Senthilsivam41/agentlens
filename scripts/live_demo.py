"""Prepare a local Agent Lens live demo: stack health, optional semantic seed, evidence file."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "docs/demo-evidence/live-demo-latest.json"
COMPOSE_FILE = ROOT / "infra/compose/docker-compose.yaml"
DEFAULT_API_URL = "http://localhost:18000"
DEFAULT_WEB_URL = "http://localhost:3000"
ASSEMBLY_WAIT_SECONDS = 25


def _request(url: str, *, timeout: float = 10) -> object:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def _http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _git_branch() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=ROOT,
                text=True,
            )
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _ensure_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.is_file():
        example = ROOT / ".env.example"
        if not example.is_file():
            raise SystemExit("Missing .env and .env.example")
        env_file.write_text(example.read_text())
        print("Created .env from .env.example — set secrets before production use.")


def _compose_up() -> None:
    subprocess.run(
        ["make", "compose-up"],
        cwd=ROOT,
        check=True,
    )


def _wait_for_api(api_url: str, deadline: float = 120) -> None:
    ready_url = f"{api_url.rstrip('/')}/health/ready"
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        try:
            payload = _request(ready_url)
            if isinstance(payload, dict) and payload.get("status") == "ready":
                return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
            pass
        time.sleep(2)
    raise TimeoutError(f"API not ready at {ready_url} within {deadline}s")


def _wait_for_execution(api_url: str, trace_id: str, deadline: float = 60) -> None:
    url = f"{api_url.rstrip('/')}/v1/executions/{trace_id}"
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        try:
            payload = _request(url)
            if isinstance(payload, dict) and payload.get("trace_id") == trace_id:
                return
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
        time.sleep(1)
    raise TimeoutError(f"execution {trace_id} not queryable within {deadline}s")


def _run_smoke_trace() -> str:
    result = subprocess.run(
        ["uv", "run", "python", "scripts/smoke_trace.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    trace_id = result.stdout.strip().splitlines()[-1].strip()
    if len(trace_id) != 32:
        raise RuntimeError(f"unexpected smoke trace output: {result.stdout!r}")
    return trace_id


def _run_semantic_acceptance() -> dict[str, object]:
    env = os.environ.copy()
    env_file = ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env.setdefault(key.strip(), value.strip())
    if not env.get("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is required for full demo mode. "
            "Set it in .env or use --mode structural."
        )
    result = subprocess.run(
        ["uv", "run", "python", "scripts/semantic_acceptance.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    for line in reversed(result.stdout.splitlines()):
        stripped = line.strip()
        if stripped.startswith("{"):
            payload = json.loads(stripped)
            if isinstance(payload, dict):
                return payload
    raise RuntimeError("semantic acceptance did not emit JSON on stdout")


def _walkthrough_urls(api_url: str, web_url: str, trace_id: str) -> dict[str, str]:
    base_api = api_url.rstrip("/")
    base_web = web_url.rstrip("/")
    return {
        "dashboard_overview": f"{base_web}/",
        "dashboard_executions": f"{base_web}/executions",
        "dashboard_baselines": f"{base_web}/baselines",
        "dashboard_execution_detail": f"{base_web}/executions/{trace_id}",
        "api_docs": f"{base_api}/docs",
        "api_summary": f"{base_api}/v1/metrics/summary",
        "api_findings": f"{base_api}/v1/findings?limit=8",
    }


def _write_evidence(payload: dict[str, object]) -> None:
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _print_summary(evidence: dict[str, object]) -> None:
    mode = evidence.get("mode")
    print(f"\nAgent Lens live demo ready ({mode}).")
    print(f"Evidence: {EVIDENCE_PATH.relative_to(ROOT)}")
    walkthrough = evidence.get("walkthrough")
    if isinstance(walkthrough, dict):
        print("\nOpen in browser:")
        for key in (
            "dashboard_overview",
            "dashboard_baselines",
            "dashboard_execution_detail",
            "api_docs",
        ):
            url = walkthrough.get(key)
            if isinstance(url, str):
                print(f"  {key}: {url}")
    if mode == "full":
        semantic = evidence.get("semantic_acceptance")
        if isinstance(semantic, dict):
            print("\nSemantic acceptance:")
            for field in ("trace_id", "baseline_id", "mahalanobis_distance", "finding_count"):
                print(f"  {field}: {semantic.get(field)}")
    elif mode == "structural":
        smoke = evidence.get("fallback_smoke")
        if isinstance(smoke, dict):
            print(f"\nSmoke trace_id: {smoke.get('trace_id')}")
            print("Expect structural_only scores (no embedding key required).")


def run_check(*, api_url: str, web_url: str) -> dict[str, object]:
    _wait_for_api(api_url)
    checks = {
        "api_ready": _http_ok(f"{api_url.rstrip('/')}/health/ready"),
        "dashboard": _http_ok(f"{web_url.rstrip('/')}/"),
        "api_docs": _http_ok(f"{api_url.rstrip('/')}/docs"),
    }
    if not all(checks.values()):
        raise SystemExit(f"health checks failed: {checks}")
    evidence: dict[str, object] = {
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "git_branch": _git_branch(),
        "mode": "check",
        "health": checks,
    }
    if EVIDENCE_PATH.is_file():
        try:
            prior = json.loads(EVIDENCE_PATH.read_text())
            if isinstance(prior, dict):
                evidence["prior_evidence"] = prior
        except json.JSONDecodeError:
            pass
    _write_evidence(evidence)
    return evidence


def run_structural(*, api_url: str, web_url: str, skip_compose: bool) -> dict[str, object]:
    if not skip_compose:
        _compose_up()
    _wait_for_api(api_url)
    trace_id = _run_smoke_trace()
    print(f"Emitted smoke trace {trace_id}; waiting for assembly (~{ASSEMBLY_WAIT_SECONDS}s)...")
    time.sleep(ASSEMBLY_WAIT_SECONDS)
    _wait_for_execution(api_url, trace_id)
    evidence: dict[str, object] = {
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "git_branch": _git_branch(),
        "mode": "structural",
        "walkthrough": _walkthrough_urls(api_url, web_url, trace_id),
        "fallback_smoke": {
            "script": "uv run python scripts/smoke_trace.py",
            "trace_id": trace_id,
            "agent_name": "pilot-smoke-agent",
            "dashboard_execution_detail": f"{web_url.rstrip('/')}/executions/{trace_id}",
            "note": "Structural-only path; no embedding key required.",
        },
    }
    _write_evidence(evidence)
    return evidence


def run_full(*, api_url: str, web_url: str, skip_compose: bool) -> dict[str, object]:
    if not skip_compose:
        _compose_up()
    _wait_for_api(api_url)
    print("Running semantic acceptance (baseline import, activate, score, findings)...")
    semantic = _run_semantic_acceptance()
    trace_id = str(semantic["trace_id"])
    baseline_id = str(semantic["baseline_id"])
    score_detail: dict[str, object] = {}
    try:
        scores = _request(f"{api_url.rstrip('/')}/v1/executions/{trace_id}/scores")
        if isinstance(scores, list):
            complete = [
                item
                for item in scores
                if isinstance(item, dict) and item.get("status") == "complete"
            ]
            if complete:
                score_detail = complete[0]
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        pass
    evidence: dict[str, object] = {
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "git_branch": _git_branch(),
        "mode": "full",
        "semantic_acceptance": semantic,
        "walkthrough": _walkthrough_urls(api_url, web_url, trace_id),
        "demo_b_talking_points": {
            "agent_name": "semantic-acceptance-agent",
            "baseline_id": baseline_id,
            "baseline_records": 500,
            "embedding_model": "text-embedding-3-small",
            "root_cause": score_detail.get("root_cause", "user_prompt_ambiguity"),
            "rationale": score_detail.get("rationale", []),
        },
        "fallback_smoke": {
            "script": "uv run python scripts/smoke_trace.py",
            "note": (
                "Use if semantic path fails mid-demo; "
                "wait ~20s before opening execution detail."
            ),
        },
    }
    _write_evidence(evidence)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Agent Lens local live demo evidence.")
    parser.add_argument(
        "--mode",
        choices=("check", "structural", "full"),
        default="full",
        help="check=health only; structural=smoke trace; full=semantic acceptance",
    )
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--web-url", default=DEFAULT_WEB_URL)
    parser.add_argument(
        "--skip-compose",
        action="store_true",
        help="Skip make compose-up (stack already running)",
    )
    args = parser.parse_args()
    _ensure_env()
    if args.mode == "check":
        evidence = run_check(api_url=args.api_url, web_url=args.web_url)
    elif args.mode == "structural":
        evidence = run_structural(
            api_url=args.api_url, web_url=args.web_url, skip_compose=args.skip_compose
        )
    else:
        evidence = run_full(
            api_url=args.api_url,
            web_url=args.web_url,
            skip_compose=args.skip_compose,
        )
    _print_summary(evidence)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"command failed with exit {exc.returncode}", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        sys.exit(exc.returncode)
    except (TimeoutError, RuntimeError, SystemExit) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
