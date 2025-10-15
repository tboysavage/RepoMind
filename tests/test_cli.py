from __future__ import annotations

from pathlib import Path

import pytest

from repo_surgeon.cli import RepoSurgeon, list_detectors, main
from repo_surgeon.detectors.base import Detector, Issue, registry


class _CliDetector(Detector):
    name = "cli"
    description = "CLI detector"

    def detect(self, root: Path):
        yield Issue(detector=self.name, message="problem", path="file.py", severity="info")


def _install_detector():
    registry.register(_CliDetector, overwrite=True)


def _uninstall_detector():
    try:
        registry.unregister("cli")
    except KeyError:
        pass


def test_repo_surgeon_run(tmp_path: Path) -> None:
    _install_detector()
    try:
        surgeon = RepoSurgeon(tmp_path)
        issues = surgeon.run()
        assert len(issues) == 1
        assert issues[0].detector == "cli"
    finally:
        _uninstall_detector()


def test_list_detectors(capsys) -> None:
    _install_detector()
    try:
        output = list_detectors()
        assert "cli" in output
    finally:
        _uninstall_detector()


def test_cli_scan_json_output(tmp_path: Path, capsys) -> None:
    _install_detector()
    try:
        exit_code = main(["scan", str(tmp_path), "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "cli" in captured.out
    finally:
        _uninstall_detector()
