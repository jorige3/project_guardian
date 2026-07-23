# Project Guardian

[![Version](https://img.shields.io/badge/version-v1.1.0-blue.svg)](https://semver.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Project Guardian is a lightweight, modular static code analysis engine for Python codebases. It is designed to audit code quality, check dependency constraints, scan for security vulnerabilities, and verify machine learning pipeline structures. Built with high extensibility, robustness, and performance in mind, Project Guardian leverages Abstract Syntax Tree (AST) parsing, Dependency Injection (DI), optional thread-pool concurrency, and structured configuration management.

---

## Key Features & Analyzers

Project Guardian uses a modular pipeline architecture with standard library-based analyzers:

1.  **LineLengthAnalyzer (`CodeReview`, `ArchitectureReview`, `PerformanceReview`)**: Scans Python files against configurable line length thresholds (defaulting to 300, 500, or 300 respectively) to enforce styling and warn about overly complex files.
2.  **SecurityReviewAnalyzer (`SecurityReview`)**: Uses AST analysis to inspect code structures and flag high-risk functions such as `eval()`, `exec()`, and `pickle.loads()`.
3.  **MLReviewAnalyzer (`MLReview`)**: Inspects machine learning pipeline imports to verify that if `sklearn` is used, split validation utilities (`train_test_split`) are not missing.
4.  **DependencyReviewAnalyzer (`DependencyReview`)**: Scans `requirements.txt` files to ensure that all dependencies are strictly version-pinned using `==`.

---

## Architecture Overview

Project Guardian's processing pipeline is divided into clear, decoupled components:

1.  **Orchestrator (`ProjectGuardian`)**: Coordinates execution by loading configuration, invoking the scanner, parallelizing or sequentially running AST-based rule analyzers, and forwarding findings to the report writer.
2.  **File Scanner (`FileScanner`)**: Walk filesystem directories, pruning excluded paths/hidden folders and ignoring symbolic links to prevent loop cycles.
3.  **Rule Engine (`BaseAnalyzer`)**: Decoupled interface defining the abstract analyzer rule contracts.
4.  **Report Writer (`ReportWriter`)**: Serializes results into markdown summaries, handling I/O permissions safely.
5.  **Configuration Manager (`Config`)**: Handles JSON configuration parsing, strict type-checking, property validations, and safe defaults.

---

## Installation & Setup with uv

Project Guardian is managed using [uv](https://github.com/astral-sh/uv).

To set up the development environment:

```bash
# Clone the repository
git clone https://github.com/kishorejorige/project_guardian.git
cd project_guardian

# Sync dependencies and build/install the local package in editable mode
uv sync --dev
```

This creates a virtual environment under `.venv/` and registers the `project-guardian` command-line executable.

---

## CLI Usage

Project Guardian is run via the `project-guardian` console script (or using `uv run project-guardian`).

### CLI Help

To show options and subcommands:

```bash
uv run project-guardian --help
```

### Show Version

To print the application version without specifying a target directory:

```bash
uv run project-guardian --version
```

### System Diagnostics (doctor)

To verify the local runtime health, modules, file permissions, and environment setup:

```bash
uv run project-guardian doctor
```

The doctor command evaluates:
*   Application version
*   Python version (requires `>=3.12`)
*   Operating system details
*   Package metadata status
*   Analyzer module imports
*   Config loading (`guardian.json`)
*   Temporary file creation and cleanup
*   Report directory writability
*   Git executable availability
*   Standard library dependencies

It returns an overall status: `healthy`, `warnings`, or `failed` (exiting with code `0` on healthy/warnings and code `1` on failed).

### Repository Scan (scan)

To scan a specific repository (scanning does not run automatically on the current working directory, a path is required):

```bash
uv run project-guardian scan /path/to/project
```

#### Scan Output:
```text
Findings: 1
- [HIGH] /path/to/project/main.py: Security risk detected: eval(
Report generated: /path/to/project/reports/project_audit.md
```

---

## Configuration (`guardian.json`)

To customize scans, create a `guardian.json` file in your project path root.

### Example Configuration:
```json
{
  "max_workers": 4,
  "exclude_dirs": ["venv", "node_modules", "dist", "build"],
  "exclude_patterns": ["temp_*", "test_*"],
  "report_path": "reports/project_audit.md",
  "analyzers": {
    "CodeReview": {
      "enabled": true,
      "threshold": 300
    },
    "SecurityReview": {
      "enabled": true
    }
  }
}
```

---

## Docker Usage

The project includes an optimized Docker configuration to build and validate the environment:

### Build Image
```bash
docker build -t project-guardian:local .
```

### Run Diagnostics
Runs the doctor command inside the container as a non-root (`guardian`) user:
```bash
docker run --rm project-guardian:local
```

---

## Testing

Project Guardian uses `pytest` and `pytest-cov` to maintain a robust, high-fidelity test suite.

Run all tests:
```bash
uv run pytest
```

---

## Quality & Security Checks

### Linting & Formatting
[Ruff](https://github.com/astral-sh/ruff) is used to maintain code quality:
```bash
# Check code style rules
uv run ruff check .

# Validate formatting
uv run ruff format --check .
```

### Security Scanning
[Bandit](https://github.com/PyCQA/bandit) scans for python security bugs:
```bash
uv run bandit -r analyzers services agent.py
```

### Dependency Audit
[pip-audit](https://github.com/pypa/pip-audit) checks for known package vulnerabilities:
```bash
uv run pip-audit
```

---

## Continuous Integration & Workflows

Workflows are located in `.github/workflows/`:
1.  **CI (`ci.yml`)**: Runs Ruff check, Ruff format check, Pytest suite, CLI command validations (`--version`, `doctor`), and Docker build/validation on every push/PR.
2.  **Security Scan (`security.yml`)**: Runs Bandit and pip-audit on Python 3.12 via `uv` on pushes/PRs to main, weekly, and on manual dispatch.
3.  **CodeQL (`codeql.yml`)**: Uses GitHub's official CodeQL actions for deep Python source analysis weekly and on pushes to main.

---

## Limitations

*   **Standard Library Only**: Core analyzers are built using standard libraries to avoid external runtimes, which limits scanning capabilities for complex framework-specific security flaws.
*   **Static AST**: Does not evaluate dynamic execution code paths or dynamic runtime imports.

---

## Roadmap

*   CLI scan depth controls
*   HTML/JSON report generation
*   Custom third-party analyzer plugin support
*   Git-diff conscious scanning (only scanning changed files)

---

## License

Distributed under the MIT License. See the LICENSE file for details.

---

## Author

**Kishore Kumar**
Python Developer
GitHub: [https://github.com/kishorejorige](https://github.com/kishorejorige)
