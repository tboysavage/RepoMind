"""Command line interface for Repo-Surgeon."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List, Sequence

from .detectors.base import Issue, registry
from .fs import ensure_path
from .tracing import JSONLTraceWriter, Tracer


class RepoSurgeon:
    """Coordinates detector execution for a repository."""

    def __init__(self, root: Path | str, *, tracer: Tracer | None = None) -> None:
        self.root = ensure_path(root)
        self.tracer = tracer or Tracer()

    def run(
        self,
        *,
        include: Sequence[str] | None = None,
        exclude: Sequence[str] | None = None,
    ) -> List[Issue]:
        """Execute detectors returning a list of issues."""

        detectors = registry.instantiate_all(
            include=include,
            exclude=exclude,
            tracer_factory=lambda name: self.tracer.child(detector=name),
        )
        issues: List[Issue] = []
        with self.tracer.span("scan", root=str(self.root)) as tracer:
            for detector in detectors:
                for issue in detector.run(self.root):
                    issues.append(issue)
            tracer.emit("scan.complete", issues=len(issues))
        return issues


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="repo-surgeon", description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Run detectors against a repository")
    scan_parser.add_argument("path", nargs="?", default=".", help="Repository path")
    scan_parser.add_argument(
        "--include",
        nargs="*",
        default=None,
        help="Only run the specified detectors",
    )
    scan_parser.add_argument(
        "--exclude",
        nargs="*",
        default=None,
        help="Skip the specified detectors",
    )
    scan_parser.add_argument(
        "--format",
        choices={"text", "json"},
        default="text",
        help="Output format",
    )
    scan_parser.add_argument(
        "--trace",
        type=Path,
        help="Write trace events to the provided JSONL file",
    )

    subparsers.add_parser("list", help="List available detectors")

    return parser


def _format_text(issues: Iterable[Issue]) -> str:
    lines = []
    for issue in issues:
        location = issue.path
        if issue.line is not None:
            location = f"{location}:{issue.line}"
        lines.append(f"{location}: {issue.severity}: {issue.message} ({issue.detector})")
    return "\n".join(lines)


def _format_json(issues: Iterable[Issue]) -> str:
    return json.dumps([issue.to_dict() for issue in issues], indent=2, sort_keys=True)


def list_detectors() -> str:
    rows = []
    for name, detector_cls in registry.available():
        rows.append(f"{name}\t{detector_cls.description}")
    return "\n".join(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "list":
        print(list_detectors())
        return 0
    if args.command != "scan":
        parser.print_help()
        return 1

    tracer = Tracer()
    trace_writer = None
    if args.trace:
        trace_writer = JSONLTraceWriter(args.trace)
        tracer = Tracer(sink=trace_writer)

    surgeon = RepoSurgeon(args.path, tracer=tracer)
    issues = surgeon.run(include=args.include, exclude=args.exclude)

    if args.format == "json":
        output = _format_json(issues)
    else:
        output = _format_text(issues)
    if output:
        print(output)

    if trace_writer is not None:
        trace_writer.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
