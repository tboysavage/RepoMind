from __future__ import annotations

from pathlib import Path

import pytest

from repo_surgeon.detectors.base import Detector, DetectorRegistry, Issue


class _ExampleDetector(Detector):
    name = "example"
    description = "Example detector"

    def detect(self, root: Path):
        yield Issue(detector=self.name, message="found", path="file.py")


class _OtherDetector(Detector):
    name = "other"
    description = "Other detector"

    def detect(self, root: Path):
        yield Issue(detector=self.name, message="other", path="file.py")


def test_register_and_instantiate(tmp_path: Path) -> None:
    registry = DetectorRegistry()
    registry.register(_ExampleDetector)
    detector = registry.create("example")
    issues = list(detector.run(tmp_path))
    assert len(issues) == 1
    assert issues[0].message == "found"


def test_instantiate_with_filters(tmp_path: Path) -> None:
    registry = DetectorRegistry()
    registry.register(_ExampleDetector)
    registry.register(_OtherDetector)

    detectors = registry.instantiate_all(include=["example"])
    assert [detector.name for detector in detectors] == ["example"]

    detectors = registry.instantiate_all(exclude=["example"])
    assert [detector.name for detector in detectors] == ["other"]


def test_register_duplicate_raises() -> None:
    registry = DetectorRegistry()
    registry.register(_ExampleDetector)
    with pytest.raises(ValueError):
        registry.register(_ExampleDetector)
