"""Tracing helpers for Repo-Surgeon."""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional


@dataclass(slots=True)
class TraceEvent:
    """A single event captured during execution."""

    timestamp: datetime
    event: str
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "timestamp": self.timestamp.isoformat(timespec="milliseconds"),
            "event": self.event,
            **self.data,
        }
        return payload


class Tracer:
    """Collects structured trace events."""

    def __init__(
        self,
        sink: Optional[Callable[[TraceEvent], None]] = None,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        _events: Optional[List[TraceEvent]] = None,
        _context: Optional[Dict[str, Any]] = None,
        _lock: Optional[threading.Lock] = None,
    ) -> None:
        self._sink = sink
        self._clock = clock
        self._events: List[TraceEvent] = _events if _events is not None else []
        self._context: Dict[str, Any] = _context if _context is not None else {}
        self._lock = _lock or threading.Lock()

    # Event recording ------------------------------------------------------
    def emit(self, event: str, /, **data: Any) -> TraceEvent:
        payload = {**self._context, **data}
        trace_event = TraceEvent(self._clock(), event, payload)
        with self._lock:
            self._events.append(trace_event)
            sink = self._sink
        if sink is not None:
            sink(trace_event)
        return trace_event

    def events(self) -> List[TraceEvent]:
        """Return a copy of recorded events."""

        with self._lock:
            return list(self._events)

    # Context management ---------------------------------------------------
    def child(self, **context: Any) -> "Tracer":
        """Return a new tracer that inherits context from this tracer."""

        merged_context = {**self._context, **context}
        return Tracer(
            sink=self._sink,
            clock=self._clock,
            _events=self._events,
            _context=merged_context,
            _lock=self._lock,
        )

    @contextmanager
    def span(self, name: str, /, **context: Any) -> Iterator["Tracer"]:
        """Context manager that emits start/end events."""

        tracer = self.child(span=name, **context)
        tracer.emit("span.start")
        try:
            yield tracer
        finally:
            tracer.emit("span.end")


class JSONLTraceWriter:
    """Persist trace events as JSON Lines."""

    def __init__(self, path: Path | str, *, ensure_parent: bool = True) -> None:
        self.path = Path(path)
        if ensure_parent:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = self.path.open("a", encoding="utf-8")
        self._lock = threading.Lock()

    def __call__(self, event: TraceEvent) -> None:
        line = json.dumps(event.to_dict(), sort_keys=True)
        with self._lock:
            self._fp.write(line + "\n")
            self._fp.flush()

    def close(self) -> None:
        with self._lock:
            if not self._fp.closed:
                self._fp.close()

    def __enter__(self) -> "JSONLTraceWriter":  # pragma: no cover - convenience
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - convenience
        self.close()


def dump_events(events: Iterable[TraceEvent]) -> str:
    """Return a JSON string representing *events*."""

    return "\n".join(json.dumps(event.to_dict(), sort_keys=True) for event in events)
