"""Repo-Surgeon: a dry-run repository auditing agent."""

from __future__ import annotations

from .cli import RepoSurgeon, main
from .detectors.base import Detector, DetectorRegistry, Issue
from .tracing import JSONLTraceWriter, TraceEvent, Tracer

__all__ = [
    "Detector",
    "DetectorRegistry",
    "Issue",
    "RepoSurgeon",
    "Tracer",
    "TraceEvent",
    "JSONLTraceWriter",
    "main",
]

__version__ = "0.1.0"
