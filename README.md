# Project Guardian

[![Version](https://img.shields.io/badge/version-v1.0.0-blue.svg)](https://semver.org)
[![Coverage](https://img.shields.io/badge/coverage-97%25-green.svg)](#testing)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Project Guardian is a lightweight, modular static code analysis engine for Python codebases. It is designed to audit code quality, check dependency constraints, scan for security vulnerabilities, and verify machine learning pipeline structures. Built with high extensibility, robustness, and performance in mind, Project Guardian leverages Abstract Syntax Tree (AST) parsing, Dependency Injection (DI), optional thread-pool concurrency, and structured configuration management.

---

## Key Features

*   **Dependency Injection**: Modular pipeline architecture that allows custom scanners, analyzers, and report writers to be injected dynamically at runtime.
*   **AST-Based Analyzers**: High-fidelity static rules using Python's built-in `ast` module to prevent false-positives on comments, docstrings, or plain-text matches.
*   **Optional Parallel Analysis**: Performance-focused concurrent execution using `ThreadPoolExecutor` to speed up scans on disk-bound codebases (defaulting to safe, single-threaded sequential execution).
*   **Configurable Ignored Files & Directories**: Built-in wildcard support using standard `fnmatch` patterns (e.g. `temp_*`) and customizable target directories.
*   **Deterministic Ordering**: Scan outputs and reports are consistently sorted alphabetically by file path, regardless of thread pool completion order.
*   **Fail-Fast Configuration**: Strict type and property validations on `guardian.json` settings, raising detailed errors on explicit typos or invalid configurations while safely falling back to defaults for missing keys.
*   **Resilient Traversals**: Isolation of directory permission errors, file OS failures, and worker thread crashes, allowing scans to continue gracefully without crashing the process.

---

## Architecture Overview

Project Guardian's pipeline is divided into clear, decoupled components:

1.  **Orchestrator (`ProjectGuardian`)**: Coordinates the analysis by loading configuration, calling the scanner to find Python files, pre-reading content/ASTs to optimize CPU execution, running rules in parallel or sequentially, and forwarding findings to the writer.
2.  **File Scanner (`FileScanner`)**: Walks the filesystem using `os.walk` to find files. Prunes excluded paths and ignores hidden dot-directories or symbolic links to prevent circular loop cycles.
3.  **Rule Engine (`BaseAnalyzer`)**: An abstract interface defining the rule contract. Concrete implementations include:
    *   `LineLengthAnalyzer`: Scans files against configurable length thresholds.
    *   `SecurityReviewAnalyzer`: Uses AST analysis to flag usage of `eval()`, `exec()`, and `pickle.loads()`.
    *   `MLReviewAnalyzer`: Inspects imports to check if `sklearn` is imported but split logic (`train_test_split`) is omitted.
    *   `DependencyReviewAnalyzer`: Scans `requirements.txt` to verify dependency versions are strictly pinned (using `==`).
4.  **Report Writer (`ReportWriter`)**: serializes audit findings to a markdown file, encapsulating I/O error handling.
5.  **Configuration Manager (`Config`)**: Separate loading module that handles JSON syntax parsing, schema validation, and maps settings to Project Guardian's parameters.

---

## Project Structure

```text
project_guardian/
├── agent.py                 # Core Orchestrator (ProjectGuardian) & CLI Entry Point
├── analyzers/
│   ├── __init__.py
│   ├── base.py              # Abstract Rule Interface (BaseAnalyzer)
│   ├── line_length.py       # Threshold Line Counter
│   ├── security_review.py   # AST Security Auditor
│   ├── ml_review.py         # AST Machine Learning Validator
│   └── dependency_review.py # requirements.txt Pin Checker
├── models/
│   ├── __init__.py
│   └── finding.py           # Data Model for Findings
├── services/
│   ├── __init__.py
│   ├── file_scanner.py      # Resilient Directory Traversal
│   ├── report_writer.py     # Safe Markdown Serializer
│   └── config_manager.py    # Configuration Validator and Schema Loader
├── tests/                   # Pytest Suite (100% coverage on core services)
│   ├── test_config.py
│   ├── test_dependency_review.py
│   ├── test_di.py
│   ├── test_line_length.py
│   ├── test_ml_review.py
│   ├── test_report_writer.py
│   ├── test_scanner.py
│   └── test_security_review.py
├── pytest.ini               # Test Suite Configuration
└── requirements.txt         # Dev dependencies (pytest, pytest-cov)
```

---

## Requirements

*   **Python**: Version 3.11 or later.
*   **Standard Library Only**: Core functionality runs entirely on Python's built-in modules. No external runtime libraries are required.

---

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/project-guardian.git
    cd project-guardian
    ```

2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  Install development/test dependencies:
    ```bash
    pip install -r requirements.txt
    ```

---

## CLI Usage

Run Project Guardian on the current directory:
```bash
python agent.py
```

### Output:
```text
Findings: 0
Report generated: reports/project_audit.md
```

If findings are detected during scanning, they are printed to the console stdout and appended to the markdown report in the configured path.

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
    },
    "ArchitectureReview": {
      "enabled": false
    }
  }
}
```

### Validation Behavior
*   **Safe Defaults**: Missing configuration files or omitted optional keys fall back to standard built-in defaults.
*   **Fail-Fast Validation**: If a config file is present but malformed, contains unknown configuration parameters, or uses incorrect data types, it raises a detailed `ConfigurationError` explaining the issue.

---

## Example Report Output

When findings are written to the report file (e.g. `reports/project_audit.md`), they follow this structure:

```markdown
# Project Audit Report

- [LOW] C:/project/main.py: File exceeds 300 lines
- [MEDIUM] C:/project/ml_model.py: ML model uses sklearn but train_test_split is not imported
- [HIGH] C:/project/db.py: Security risk detected: exec(
```

---

## Testing

Project Guardian uses `pytest` and `pytest-cov` to maintain a robust, high-fidelity test suite.

Run the test suite:
```bash
pytest
```

Run tests with line coverage analysis:
```bash
pytest --cov=. --cov-report=term-missing
```

### Test Coverage Status
Project Guardian maintains a strict minimum test coverage of **97%**:
*   `services/config_manager.py`: **100% coverage**
*   `services/file_scanner.py`: **100% coverage**
*   `services/report_writer.py`: **100% coverage**
*   `tests/`: **100% coverage**

---

## Versioning & Architecture Milestones

Current Release: **v1.0.0** (Stable Production Release)

### Roadmap
*   **v0.5.0** - Core Dependency Injection and basic Analyzers.
*   **v0.7.0** - AST-based Rule refactoring and File Scanner improvements.
*   **v0.8.0** - Concurrency and Performance Optimization.
*   **v0.9.0** - JSON Schema Configuration Management (Current).
*   **v1.0.0** - Continuous Integration workflow and CLI argument parsing support.

### Completed

- ✅ Dependency Injection
- ✅ AST-based analysis
- ✅ Configuration Management
- ✅ Performance optimization
- ✅ Optional Parallel Analysis
- ✅ Robust File Scanner
- ✅ Report Generation

### Future Ideas

- CLI argument support
- GitHub Actions CI
- Additional analyzers
- HTML report generation
- Plugin architecture

## Contributing

1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## License

Distributed under the MIT License. See the LICENSE file for details.
