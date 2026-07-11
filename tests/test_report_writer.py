from pathlib import Path
from unittest.mock import patch
import pytest

from services.report_writer import ReportWriter, ReportWriteError
from models.finding import Finding


def test_successful_report_creation(tmp_path):
    writer = ReportWriter()
    output_file = tmp_path / "subdir" / "audit.md"
    
    findings = [
        Finding(
            analyzer="TestAnalyzer",
            severity="HIGH",
            file_path="src/file.py",
            message="Test finding 1"
        ),
        Finding(
            analyzer="TestAnalyzer2",
            severity="LOW",
            file_path="src/file2.py",
            message="Test finding 2"
        ),
    ]

    # Test successful write and nested directory creation
    writer.write(findings, str(output_file))

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    expected = (
        "# Project Audit Report\n\n"
        "- [HIGH] src/file.py: Test finding 1\n"
        "- [LOW] src/file2.py: Test finding 2\n"
    )
    assert content == expected


def test_empty_findings(tmp_path):
    writer = ReportWriter()
    output_file = tmp_path / "audit.md"

    writer.write([], str(output_file))

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert content == "# Project Audit Report\n\n"


def test_directory_creation_failure():
    writer = ReportWriter()
    # Mock Path.mkdir to raise PermissionError/OSError
    with patch.object(Path, "mkdir", side_effect=PermissionError("Permission denied")):
        with pytest.raises(ReportWriteError) as exc_info:
            writer.write([], "some_dir/audit.md")
        assert "Failed to create output directory" in str(exc_info.value)


def test_file_write_failure(tmp_path):
    writer = ReportWriter()
    # Mock open to raise PermissionError when writing file
    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        with pytest.raises(ReportWriteError) as exc_info:
            writer.write([], str(tmp_path / "audit.md"))
        assert "Failed to write report" in str(exc_info.value)
