"""Customer walkthrough for Agent Lens drift classifications.

    python -m drift_demo bootstrap
    python -m drift_demo traffic
    python -m drift_demo report
    python -m drift_demo all
"""

from __future__ import annotations

import argparse

from .baseline import bootstrap
from .report import report
from .traffic import send_traffic


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Lens customer drift demo")
    subcommands = parser.add_subparsers(dest="command", required=True)

    bootstrap_cmd = subcommands.add_parser("bootstrap", help="import and activate a demo baseline")
    _add_shared(bootstrap_cmd)
    bootstrap_cmd.add_argument("--records", type=int, default=500)
    bootstrap_cmd.add_argument("--deadline-seconds", type=float, default=180)

    traffic_cmd = subcommands.add_parser("traffic", help="send randomized demo traces")
    _add_shared(traffic_cmd)
    traffic_cmd.add_argument("--count", type=int, default=60)
    traffic_cmd.add_argument("--vague-ratio", type=float, default=0.4)
    traffic_cmd.add_argument("--regression-ratio", type=float, default=0.1)
    traffic_cmd.add_argument("--baseline-ref", default=None)

    report_cmd = subcommands.add_parser("report", help="compare scenarios with scored root causes")
    _add_shared(report_cmd)
    report_cmd.add_argument("--deadline-seconds", type=float, default=120)

    all_cmd = subcommands.add_parser("all", help="bootstrap, send traffic, and print the report")
    _add_shared(all_cmd)
    all_cmd.add_argument("--records", type=int, default=500)
    all_cmd.add_argument("--count", type=int, default=60)
    all_cmd.add_argument("--vague-ratio", type=float, default=0.4)
    all_cmd.add_argument("--regression-ratio", type=float, default=0.1)
    all_cmd.add_argument("--deadline-seconds", type=float, default=180)

    args = parser.parse_args()
    if args.command == "bootstrap":
        bootstrap(
            api_url=args.api_url,
            records=args.records,
            seed=args.seed,
            deadline=args.deadline_seconds,
        )
        return
    if args.command == "traffic":
        send_traffic(
            endpoint=args.edge_endpoint,
            count=args.count,
            vague_ratio=args.vague_ratio,
            regression_ratio=args.regression_ratio,
            seed=args.seed,
            baseline_ref=args.baseline_ref,
        )
        return
    if args.command == "report":
        report(
            api_url=args.api_url,
            dashboard_url=args.dashboard_url,
            deadline=args.deadline_seconds,
        )
        return
    baseline_id = bootstrap(
        api_url=args.api_url,
        records=args.records,
        seed=args.seed,
        deadline=args.deadline_seconds,
    )
    send_traffic(
        endpoint=args.edge_endpoint,
        count=args.count,
        vague_ratio=args.vague_ratio,
        regression_ratio=args.regression_ratio,
        seed=args.seed,
        baseline_ref=baseline_id,
    )
    report(
        api_url=args.api_url,
        dashboard_url=args.dashboard_url,
        deadline=args.deadline_seconds,
    )


def _add_shared(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-url", default="http://localhost:18000")
    parser.add_argument("--edge-endpoint", default="http://localhost:4317")
    parser.add_argument("--dashboard-url", default="http://localhost:3000")
    parser.add_argument("--seed", type=int, default=7)


if __name__ == "__main__":
    main()
