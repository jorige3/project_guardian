import json
import pytest
from pathlib import Path
from unittest.mock import patch
from agent import ProjectGuardian
from services.config_manager import Config, load_config_file, ConfigurationError
from services.file_scanner import FileScanner
from analyzers.line_length import LineLengthAnalyzer
from analyzers.security_review import SecurityReviewAnalyzer


def test_no_config_file_returns_defaults():
    config = load_config_file(Path("non_existent_config.json"))
    assert config.max_workers == 1
    assert "venv" in config.exclude_dirs
    assert config.report_path == "reports/project_audit.md"
    assert config.analyzers["CodeReview"]["enabled"] is True
    assert config.analyzers["CodeReview"]["threshold"] == 300


def test_default_config():
    config = Config()
    assert config.max_workers == 1
    assert config.report_path == "reports/project_audit.md"
    assert len(config.exclude_dirs) > 0
    assert "temp_*" in config.exclude_patterns


def test_partial_custom_config(tmp_path):
    config_file = tmp_path / "guardian.json"
    data = {
        "max_workers": 3,
        "report_path": "reports/custom.md"
    }
    config_file.write_text(json.dumps(data))

    config = load_config_file(config_file)
    assert config.max_workers == 3
    assert config.report_path == "reports/custom.md"
    assert "venv" in config.exclude_dirs


def test_full_custom_config(tmp_path):
    config_file = tmp_path / "guardian.json"
    data = {
        "max_workers": 5,
        "exclude_dirs": ["dist", "build"],
        "exclude_patterns": ["*.tmp", "test_*"],
        "report_path": "reports/full.md",
        "analyzers": {
            "CodeReview": {"enabled": False},
            "ArchitectureReview": {"threshold": 400},
            "SecurityReview": {"enabled": True}
        }
    }
    config_file.write_text(json.dumps(data))

    config = load_config_file(config_file)
    assert config.max_workers == 5
    assert config.exclude_dirs == {"dist", "build"}
    assert config.exclude_patterns == ["*.tmp", "test_*"]
    assert config.report_path == "reports/full.md"
    assert config.analyzers["CodeReview"]["enabled"] is False
    assert config.analyzers["ArchitectureReview"]["threshold"] == 400
    assert config.analyzers["SecurityReview"]["enabled"] is True


def test_malformed_config(tmp_path):
    config_file = tmp_path / "guardian.json"
    config_file.write_text("{invalid json}")

    with pytest.raises(ConfigurationError, match="Configuration file is malformed JSON"):
        load_config_file(config_file)


def test_invalid_value_types(tmp_path):
    config_file = tmp_path / "guardian.json"

    # max_workers is a boolean
    data = {"max_workers": True}
    config_file.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError, match="Invalid 'max_workers' value"):
        load_config_file(config_file)

    # exclude_dirs is not a list
    data = {"exclude_dirs": "venv"}
    config_file.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError, match="Invalid 'exclude_dirs'"):
        load_config_file(config_file)


def test_unknown_keys(tmp_path):
    config_file = tmp_path / "guardian.json"
    data = {"unknown_key_xyz": "value"}
    config_file.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError, match="Unknown configuration settings"):
        load_config_file(config_file)


def test_invalid_thresholds(tmp_path):
    config_file = tmp_path / "guardian.json"
    data = {
        "analyzers": {
            "CodeReview": {"threshold": -50}
        }
    }
    config_file.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError, match="Invalid 'threshold' value"):
        load_config_file(config_file)


def test_invalid_max_workers(tmp_path):
    config_file = tmp_path / "guardian.json"
    data = {"max_workers": 0}
    config_file.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError, match="Invalid 'max_workers' value"):
        load_config_file(config_file)


def test_di_config_integration(tmp_path):
    config = Config({
        "max_workers": 2,
        "report_path": "reports/di_report.md",
        "analyzers": {
            "CodeReview": {"enabled": False}
        }
    })

    guardian = ProjectGuardian(project_path=str(tmp_path), config=config)
    assert guardian.max_workers == 2
    assert guardian.report_path == "reports/di_report.md"

    analyzer_names = [a.name for a in guardian.analyzers if hasattr(a, "name")]
    assert "CodeReview" not in analyzer_names


def test_config_not_dict():
    with pytest.raises(ConfigurationError, match="Configuration data must be a dictionary"):
        Config("not a dict")


def test_invalid_exclude_patterns(tmp_path):
    config_file = tmp_path / "guardian.json"
    data = {"exclude_patterns": "not a list"}
    config_file.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError, match="Invalid 'exclude_patterns'"):
        load_config_file(config_file)


def test_invalid_report_path_empty(tmp_path):
    config_file = tmp_path / "guardian.json"
    data = {"report_path": "   "}
    config_file.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError, match="Invalid 'report_path'"):
        load_config_file(config_file)


def test_invalid_analyzers_not_dict(tmp_path):
    config_file = tmp_path / "guardian.json"
    data = {"analyzers": "not a dict"}
    config_file.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError, match="Invalid 'analyzers' configuration"):
        load_config_file(config_file)


def test_config_unknown_analyzer(tmp_path):
    config_file = tmp_path / "guardian.json"
    data = {"analyzers": {"UnknownAnalyzer": {}}}
    config_file.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError, match="Unknown analyzers configured"):
        load_config_file(config_file)


def test_config_analyzer_not_dict(tmp_path):
    config_file = tmp_path / "guardian.json"
    data = {"analyzers": {"CodeReview": "not a dict"}}
    config_file.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError, match="must be a dictionary"):
        load_config_file(config_file)


def test_config_analyzer_unknown_setting(tmp_path):
    config_file = tmp_path / "guardian.json"
    data = {"analyzers": {"CodeReview": {"unknown_setting": 1}}}
    config_file.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError, match="Unknown setting for analyzer"):
        load_config_file(config_file)


def test_config_analyzer_invalid_enabled_type(tmp_path):
    config_file = tmp_path / "guardian.json"
    data = {"analyzers": {"CodeReview": {"enabled": "not a bool"}}}
    config_file.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError, match="Must be a boolean"):
        load_config_file(config_file)


def test_config_analyzer_unsupported_threshold(tmp_path):
    config_file = tmp_path / "guardian.json"
    data = {"analyzers": {"SecurityReview": {"threshold": 100}}}
    config_file.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError, match="does not support a threshold setting"):
        load_config_file(config_file)


def test_load_config_file_os_error(tmp_path):
    config_file = tmp_path / "guardian.json"
    config_file.touch()
    with patch("builtins.open", side_effect=OSError("Read failure")):
        with pytest.raises(ConfigurationError, match="Failed to read configuration file"):
            load_config_file(config_file)


def test_exclude_patterns(tmp_path):
    (tmp_path / "temp_abc.py").touch()
    (tmp_path / "regular.py").touch()

    scanner = FileScanner(str(tmp_path), exclude_patterns=["temp_*"])
    files = scanner.get_python_files()
    assert len(files) == 1
    assert files[0].name == "regular.py"
