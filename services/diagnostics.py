import importlib.metadata
import os
import platform
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path
from services.config_manager import load_config_file, ConfigurationError


class DiagnosticsChecker:
    """Class to run project diagnostic checks and report health status."""

    def __init__(self, project_path="."):
        self.project_path = Path(project_path)
        self.results = {}
        self.errors = []
        self.warnings = []

    def check_app_version(self):
        """Checks the application version from package metadata, with fallback."""
        try:
            app_version = importlib.metadata.version("project-guardian")
            self.results["app_version"] = app_version
            self.results["package_metadata_ok"] = True
        except Exception as e:
            self.results["app_version"] = "1.1.0"
            self.results["package_metadata_ok"] = False
            self.warnings.append(f"Package metadata not found (using fallback 1.1.0): {e}")

    def check_python_version(self):
        """Checks if the Python version is >= 3.12."""
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        self.results["python_version"] = py_version
        if sys.version_info.major < 3 or sys.version_info.minor < 12:
            self.errors.append(f"Python version {py_version} is unsupported. Version >= 3.12 is required.")
        else:
            self.results["python_version_ok"] = True

    def check_operating_system(self):
        """Identifies the current operating system."""
        self.results["os"] = f"{platform.system()} {platform.release()}"

    def check_analyzer_imports(self):
        """Verifies all required analyzer modules can be imported."""
        analyzers_to_import = [
            ("analyzers.security_review", "SecurityReviewAnalyzer"),
            ("analyzers.ml_review", "MLReviewAnalyzer"),
            ("analyzers.line_length", "LineLengthAnalyzer"),
            ("analyzers.dependency_review", "DependencyReviewAnalyzer"),
        ]
        failed_imports = []
        for mod_name, class_name in analyzers_to_import:
            try:
                mod = importlib.import_module(mod_name)
                getattr(mod, class_name)
            except Exception as e:
                failed_imports.append(f"{mod_name}.{class_name} ({e})")

        if failed_imports:
            self.errors.append(f"Failed to import analyzer modules: {', '.join(failed_imports)}")
            self.results["analyzers_ok"] = False
        else:
            self.results["analyzers_ok"] = True

    def check_config_loading(self):
        """Checks if guardian.json is valid if present."""
        config_file = self.project_path / "guardian.json"
        if config_file.exists():
            try:
                load_config_file(config_file)
                self.results["config_ok"] = True
            except ConfigurationError as e:
                self.warnings.append(f"Config file guardian.json is malformed or invalid: {e}")
                self.results["config_ok"] = False
        else:
            self.results["config_ok"] = True  # Absent is healthy fallback

    def check_temp_file_creation(self):
        """Tests creation and cleanup of a temporary file."""
        try:
            with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
                temp_path = Path(f.name)
                f.write("guardian-test")
                f.flush()

            # Verify we can read it
            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Clean up
            os.remove(temp_path)

            if content == "guardian-test":
                self.results["temp_file_ok"] = True
            else:
                self.errors.append("Temporary file contents mismatch.")
                self.results["temp_file_ok"] = False
        except Exception as e:
            self.errors.append(f"Failed to create/cleanup temporary files: {e}")
            self.results["temp_file_ok"] = False

    def check_report_directory_writability(self):
        """Verifies report directory writability using a temporary location."""
        # Using a temporary location means creating a temporary file inside a temp directory
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_report_path = Path(temp_dir) / "test_report.md"
                with open(temp_report_path, "w", encoding="utf-8") as f:
                    f.write("# Test")
                if temp_report_path.exists():
                    self.results["report_dir_writability_ok"] = True
                else:
                    self.errors.append("Failed to write report in temporary directory.")
                    self.results["report_dir_writability_ok"] = False
        except Exception as e:
            self.errors.append(f"Failed to write report to temporary location: {e}")
            self.results["report_dir_writability_ok"] = False

    def check_git_availability(self):
        """Checks if the git command line tool is available."""
        try:
            res = subprocess.run(  # nosec B603 B607
                ["git", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
            )
            if res.returncode == 0:
                self.results["git_version"] = res.stdout.strip()
                self.results["git_ok"] = True
            else:
                self.warnings.append("Git command returned a non-zero exit code.")
                self.results["git_ok"] = False
        except Exception as e:
            self.warnings.append(f"Git executable not available: {e}")
            self.results["git_ok"] = False

    def check_required_dependencies(self):
        """Checks availability of standard library dependencies required by the app."""
        required_mods = [
            "pathlib",
            "json",
            "ast",
            "inspect",
            "argparse",
            "concurrent.futures",
            "fnmatch",
            "os",
            "sys",
            "platform",
            "subprocess",
            "tempfile",
        ]
        missing = []
        for mod in required_mods:
            try:
                importlib.import_module(mod)
            except ImportError:
                missing.append(mod)

        if missing:
            self.errors.append(f"Missing core standard library modules: {', '.join(missing)}")
            self.results["dependencies_ok"] = False
        else:
            self.results["dependencies_ok"] = True

    def run_all(self):
        """Runs all diagnostic checks and determines overall health status."""
        self.check_app_version()
        self.check_python_version()
        self.check_operating_system()
        self.check_analyzer_imports()
        self.check_config_loading()
        self.check_temp_file_creation()
        self.check_report_directory_writability()
        self.check_git_availability()
        self.check_required_dependencies()

        if self.errors:
            status = "failed"
        elif self.warnings:
            status = "warnings"
        else:
            status = "healthy"

        return {"status": status, "results": self.results, "errors": self.errors, "warnings": self.warnings}
