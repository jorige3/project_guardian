import importlib
from collections import namedtuple
from unittest.mock import patch, MagicMock
import pytest
from services.config_manager import Config
from services.diagnostics import DiagnosticsChecker
from agent import main, ProjectGuardian

VersionInfo = namedtuple("VersionInfo", ["major", "minor", "micro"])


def test_cli_help(capsys):
    """Test --help output and exit code."""
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "Project Guardian" in captured.out
    assert "--version" in captured.out
    assert "doctor" in captured.out
    assert "scan" in captured.out


def test_cli_version(capsys):
    """Test --version output."""
    with patch("importlib.metadata.version", return_value="1.1.0"):
        with pytest.raises(SystemExit) as excinfo:
            main(["--version"])
        assert excinfo.value.code == 0
        captured = capsys.readouterr()
        assert "Project Guardian version 1.1.0" in captured.out


def test_cli_version_fallback(capsys):
    """Test version fallback when importlib.metadata.version raises exception."""
    with patch("importlib.metadata.version", side_effect=Exception("not found")):
        with pytest.raises(SystemExit) as excinfo:
            main(["--version"])
        assert excinfo.value.code == 0
        captured = capsys.readouterr()
        assert "Project Guardian version 1.1.0" in captured.out


def test_cli_no_args(capsys):
    """Test running CLI without command shows help and exits with 1."""
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Project Guardian" in captured.out


def test_doctor_healthy(capsys):
    """Test doctor report when everything is healthy."""
    with patch("sys.version_info", VersionInfo(3, 12, 0)):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="git version 2.40.0")
            with patch("importlib.metadata.version", return_value="1.1.0"):
                with pytest.raises(SystemExit) as excinfo:
                    main(["doctor"])
                assert excinfo.value.code == 0

                captured = capsys.readouterr()
                assert "Status: HEALTHY" in captured.out
                assert "Errors:" not in captured.out
                assert "Warnings:" not in captured.out


def test_doctor_warning_behavior(capsys):
    """Test doctor report warning status (e.g. Git missing)."""
    with patch("sys.version_info", VersionInfo(3, 12, 0)):
        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            with pytest.raises(SystemExit) as excinfo:
                main(["doctor"])
            assert excinfo.value.code == 0

            captured = capsys.readouterr()
            assert "Status: WARNINGS" in captured.out
            assert "Warnings:" in captured.out
            assert "Git executable not available" in captured.out


def test_doctor_critical_failure(capsys):
    """Test doctor report failure status (e.g. unsupported Python version)."""
    with patch("sys.version_info", VersionInfo(3, 11, 0)):
        with pytest.raises(SystemExit) as excinfo:
            main(["doctor"])
        assert excinfo.value.code == 1

        captured = capsys.readouterr()
        assert "Status: FAILED" in captured.out
        assert "Errors:" in captured.out
        assert "Python version 3.11.0 is unsupported" in captured.out


def test_doctor_analyzer_import_failure(capsys):
    """Test doctor behavior when an analyzer module fails to import."""
    with patch("importlib.import_module", side_effect=ImportError("mocked import error")):
        with pytest.raises(SystemExit) as excinfo:
            main(["doctor"])
        assert excinfo.value.code == 1

        captured = capsys.readouterr()
        assert "Status: FAILED" in captured.out
        assert "Failed to import analyzer modules" in captured.out


def test_doctor_config_loading_warning(capsys, tmp_path):
    """Test doctor warning behavior with a malformed configuration file."""
    # Write a malformed config inside the project path
    config_file = tmp_path / "guardian.json"
    config_file.write_text("{invalid_json}")

    # We patch __init__ of DiagnosticsChecker to override project_path
    original_init = DiagnosticsChecker.__init__

    def mock_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.project_path = tmp_path

    with patch.object(DiagnosticsChecker, "__init__", mock_init):
        with patch("sys.version_info", VersionInfo(3, 12, 0)):
            with pytest.raises(SystemExit) as excinfo:
                main(["doctor"])
            assert excinfo.value.code == 0

            captured = capsys.readouterr()
            assert "Status: WARNINGS" in captured.out
            assert "Config file guardian.json is malformed" in captured.out


def test_doctor_temp_file_failure(capsys):
    """Test doctor behavior when temporary file creation fails."""
    with patch("tempfile.NamedTemporaryFile", side_effect=OSError("Permission denied")):
        with pytest.raises(SystemExit) as excinfo:
            main(["doctor"])
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Status: FAILED" in captured.out
        assert "Failed to create/cleanup temporary files" in captured.out


def test_scan_missing_path(capsys):
    """Test scan with a missing or non-existent path."""
    with pytest.raises(SystemExit) as excinfo:
        main(["scan", "/nonexistent/path/for/guardian/scan"])
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "Error: Path '/nonexistent/path/for/guardian/scan' does not exist." in captured.err


def test_scan_invalid_path(capsys, tmp_path):
    """Test scan when the path is a file instead of a directory."""
    test_file = tmp_path / "file.txt"
    test_file.touch()

    with pytest.raises(SystemExit) as excinfo:
        main(["scan", str(test_file)])
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "is not a directory" in captured.err


def test_scan_valid_temporary_repo(capsys, tmp_path):
    """Test scanning a valid temporary repository."""
    # Setup simple Python file
    py_file = tmp_path / "example.py"
    py_file.write_text("print('test')\n")

    # We should run scan CLI command on this directory
    with pytest.raises(SystemExit) as excinfo:
        main(["scan", str(tmp_path)])
    assert excinfo.value.code == 0

    captured = capsys.readouterr()
    assert "Findings: 0" in captured.out
    assert "Report generated:" in captured.out

    # Verify report is written inside the scanned directory
    report_file = tmp_path / "reports/project_audit.md"
    assert report_file.exists()
    assert "# Project Audit Report" in report_file.read_text()


def test_scan_config_error(capsys, tmp_path):
    """Test that a ConfigurationError during scan is printed cleanly without traceback."""
    py_file = tmp_path / "example.py"
    py_file.write_text("print('test')\n")
    config_file = tmp_path / "guardian.json"
    config_file.write_text("{malformed_config}")

    with pytest.raises(SystemExit) as excinfo:
        main(["scan", str(tmp_path)])
    assert excinfo.value.code == 1

    captured = capsys.readouterr()
    assert "Configuration Error" in captured.err
    # Ensure there is no traceback in stderr
    assert "Traceback" not in captured.err


def test_backward_compatibility():
    """Verify that ProjectGuardian class maintains backward compatibility."""
    # Instantiation without parameters defaults to "."
    guardian = ProjectGuardian()
    assert isinstance(guardian.config, Config)
    assert isinstance(guardian.report_path, str)


def test_diagnostics_git_version_warning(capsys):
    """Test doctor warning behavior when git outputs non-zero code."""
    with patch("sys.version_info", VersionInfo(3, 12, 0)):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=127, stdout="", stderr="command not found")
            with pytest.raises(SystemExit) as excinfo:
                main(["doctor"])
            assert excinfo.value.code == 0
            captured = capsys.readouterr()
            assert "Status: WARNINGS" in captured.out
            assert "Git command returned a non-zero exit code" in captured.out


def test_diagnostics_missing_std_libs(capsys):
    """Test diagnostics when a standard library import fails."""
    # We mock import_module to fail for os module specifically
    original_import = importlib.import_module

    def mock_import(name, *args, **kwargs):
        if name == "os":
            raise ImportError("mocked error")
        return original_import(name, *args, **kwargs)

    with patch("importlib.import_module", side_effect=mock_import):
        with pytest.raises(SystemExit) as excinfo:
            main(["doctor"])
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Status: FAILED" in captured.out
        assert "Missing core standard library modules" in captured.out
