import json
from pathlib import Path

from analyzers.security_review import SecurityReviewAnalyzer
from analyzers.ml_review import MLReviewAnalyzer
from analyzers.line_length import LineLengthAnalyzer
from analyzers.dependency_review import DependencyReviewAnalyzer


class ConfigurationError(ValueError):
    """Exception raised when configuration is malformed or invalid."""
    pass


class Config:
    # Documented Defaults
    DEFAULT_MAX_WORKERS = 1
    DEFAULT_EXCLUDE_DIRS = {
        "venv", ".venv", "tests", "__pycache__",
        ".git", ".pytest_cache", "temp_pytest", "node_modules"
    }
    DEFAULT_EXCLUDE_PATTERNS = ["temp_*"]
    DEFAULT_REPORT_PATH = "reports/project_audit.md"
    DEFAULT_ANALYZER_CONFIGS = {
        "CodeReview": {"enabled": True, "threshold": 300},
        "ArchitectureReview": {"enabled": True, "threshold": 500},
        "PerformanceReview": {"enabled": True, "threshold": 300},
        "SecurityReview": {"enabled": True},
        "MLReview": {"enabled": True},
        "DependencyReview": {"enabled": True}
    }

    def __init__(self, data=None):
        self.max_workers = self.DEFAULT_MAX_WORKERS
        self.exclude_dirs = set(self.DEFAULT_EXCLUDE_DIRS)
        self.exclude_patterns = list(self.DEFAULT_EXCLUDE_PATTERNS)
        self.report_path = self.DEFAULT_REPORT_PATH
        self.analyzers = {name: cfg.copy() for name, cfg in self.DEFAULT_ANALYZER_CONFIGS.items()}

        if data is not None:
            self._parse_and_validate(data)

    def _parse_and_validate(self, data):
        if not isinstance(data, dict):
            raise ConfigurationError("Configuration data must be a dictionary.")

        # Check for unknown settings
        known_keys = {"max_workers", "exclude_dirs", "exclude_patterns", "report_path", "analyzers"}
        unknown_keys = set(data.keys()) - known_keys
        if unknown_keys:
            raise ConfigurationError(f"Unknown configuration settings: {', '.join(unknown_keys)}")

        # max_workers validation
        if "max_workers" in data:
            val = data["max_workers"]
            if val is not None and (not isinstance(val, int) or isinstance(val, bool) or val < 1):
                raise ConfigurationError(f"Invalid 'max_workers' value: {val}. Must be an integer >= 1 or null.")
            self.max_workers = val

        # exclude_dirs validation
        if "exclude_dirs" in data:
            val = data["exclude_dirs"]
            if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                raise ConfigurationError(f"Invalid 'exclude_dirs' value: {val}. Must be a list of strings.")
            self.exclude_dirs = set(val)

        # exclude_patterns validation
        if "exclude_patterns" in data:
            val = data["exclude_patterns"]
            if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                raise ConfigurationError(f"Invalid 'exclude_patterns' value: {val}. Must be a list of strings.")
            self.exclude_patterns = list(val)

        # report_path validation
        if "report_path" in data:
            val = data["report_path"]
            if not isinstance(val, str) or not val.strip():
                raise ConfigurationError(f"Invalid 'report_path' value: {val}. Must be a non-empty string.")
            self.report_path = val.strip()

        # analyzers validation
        if "analyzers" in data:
            val = data["analyzers"]
            if not isinstance(val, dict):
                raise ConfigurationError(f"Invalid 'analyzers' configuration: {val}. Must be a dictionary.")

            # Check for unknown analyzers
            unknown_analyzers = set(val.keys()) - set(self.DEFAULT_ANALYZER_CONFIGS.keys())
            if unknown_analyzers:
                raise ConfigurationError(f"Unknown analyzers configured: {', '.join(unknown_analyzers)}")

            for name, default_cfg in self.DEFAULT_ANALYZER_CONFIGS.items():
                cfg = default_cfg.copy()
                if name in val:
                    overrides = val[name]
                    if not isinstance(overrides, dict):
                        raise ConfigurationError(f"Analyzer '{name}' configuration must be a dictionary.")

                    # Check for unknown keys in analyzer configuration
                    known_analyzer_keys = {"enabled", "threshold"}
                    unknown_analyzer_keys = set(overrides.keys()) - known_analyzer_keys
                    if unknown_analyzer_keys:
                        raise ConfigurationError(f"Unknown setting for analyzer '{name}': {', '.join(unknown_analyzer_keys)}")

                    if "enabled" in overrides:
                        enabled = overrides["enabled"]
                        if not isinstance(enabled, bool):
                            raise ConfigurationError(f"Invalid 'enabled' value for analyzer '{name}': {enabled}. Must be a boolean.")
                        cfg["enabled"] = enabled

                    if "threshold" in overrides:
                        if "threshold" not in default_cfg:
                            raise ConfigurationError(f"Analyzer '{name}' does not support a threshold setting.")
                        threshold = overrides["threshold"]
                        if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold <= 0:
                            raise ConfigurationError(f"Invalid 'threshold' value for analyzer '{name}': {threshold}. Must be a positive integer.")
                        cfg["threshold"] = threshold

                self.analyzers[name] = cfg


def load_config_file(config_path: Path) -> Config:
    """Loads and validates a configuration file.

    If the configuration file does not exist, returns a default Config object.
    If the file is malformed JSON or contains validation errors, raises ConfigurationError.
    """
    if not config_path.exists():
        return Config()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"Configuration file is malformed JSON: {e}") from e
    except OSError as e:
        raise ConfigurationError(f"Failed to read configuration file: {e}") from e

    return Config(data)
