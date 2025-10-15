from __future__ import annotations

from pathlib import Path

from repo_surgeon.tracing import JSONLTraceWriter, TraceEvent, Tracer


def test_tracer_records_events(tmp_path) -> None:
    tracer = Tracer()
    tracer.emit("start", value=1)
    with tracer.span("operation", item="x") as span_tracer:
        span_tracer.emit("step", index=1)
    events = tracer.events()
    names = [event.event for event in events]
    assert names == ["start", "span.start", "step", "span.end"]
    assert events[1].data["span"] == "operation"
    assert events[2].data["item"] == "x"


def test_jsonl_writer(tmp_path) -> None:
    path = tmp_path / "trace.jsonl"
    writer = JSONLTraceWriter(path)
    tracer = Tracer(sink=writer)
    tracer.emit("event", value=42)
    writer.close()
    content = path.read_text().strip().splitlines()
    assert len(content) == 1
    assert "value" in content[0]
