"""Direct tests for scripts/materials_validator.py package validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import materials_validator as mv


def _make_package(tmp_path):
    (tmp_path / "cover-letter.md").write_text("Dear team, I am writing about governance systems.\n")
    (tmp_path / "portal-answers.md").write_text("Q: Why?\nA: Because systems.\n")
    (tmp_path / "Jane-Resume.html").write_text("<html><body>Resume content</body></html>")
    return tmp_path


def test_validate_package_returns_report(tmp_path):
    report = mv.validate_package(_make_package(tmp_path))
    assert isinstance(report, mv.MaterialsReport)
    assert isinstance(report.results, list)
    assert report.results  # at least one article evaluated
    assert isinstance(report.valid, bool)


def test_materials_report_summary_includes_overall(tmp_path):
    report = mv.validate_package(_make_package(tmp_path))
    assert "Overall:" in report.summary()
