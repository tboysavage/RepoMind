# RepoMind

Repo-Surgeon is a dry-run code audit agent that scans your repository in seconds, surfaces potential issues, and logs every finding with full traceability. It doesn’t modify code, it just reports what it would fix.

## Features

* **Detector registry** – compose custom checks that analyse files and emit structured issues.
* **Filesystem helpers** – deterministic, configurable directory traversal optimised for tooling scenarios.
* **Structured tracing** – JSONL trace writer with context propagation to observe detector execution.
* **CLI utility** – run the engine from the command line, list detectors, and export findings as JSON.

## Quick start

Install the project in editable mode and invoke the CLI:

```bash
pip install -e .
repo-surgeon scan path/to/repo --format json --trace traces/run.jsonl
```

## Development

```bash
pip install -e .[dev]
pytest
```

Traces are stored as JSON Lines. A sample trace is available in `traces/sample.run.jsonl`.
