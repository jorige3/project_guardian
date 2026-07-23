from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from services.file_scanner import FileScanner
from services.report_writer import ReportWriter
from services.config_manager import load_config_file, ConfigurationError
from analyzers.security_review import SecurityReviewAnalyzer
from analyzers.ml_review import MLReviewAnalyzer
from analyzers.line_length import LineLengthAnalyzer
from analyzers.dependency_review import DependencyReviewAnalyzer
import argparse
import sys
from services.diagnostics import DiagnosticsChecker


class ProjectGuardian:
    def __init__(
        self, project_path=".", scanner=None, analyzers=None, report_writer=None, max_workers=None, config=None
    ):
        self.project_path = Path(project_path)

        # Config loading: priority is injected config -> file loading -> defaults
        if config is not None:
            self.config = config
        else:
            self.config = load_config_file(self.project_path / "guardian.json")

        # Resolve scanner with config priorities
        if scanner is not None:
            self.scanner = scanner
        else:
            self.scanner = FileScanner(
                str(self.project_path),
                exclude_dirs=self.config.exclude_dirs,
                exclude_patterns=self.config.exclude_patterns,
            )

        # Resolve report_writer and report_path
        self.report_writer = report_writer if report_writer is not None else ReportWriter()
        self.report_path = self.config.report_path

        # Resolve max_workers priority: Constructor parameter -> Config -> default
        if max_workers is not None:
            self.max_workers = max_workers
        else:
            self.max_workers = self.config.max_workers

        # Normalize max_workers count
        if self.max_workers is not None and self.max_workers < 1:
            self.max_workers = 1

        # Resolve analyzers
        if analyzers is not None:
            self.analyzers = analyzers
        else:
            self.analyzers = []
            for name, cfg in self.config.analyzers.items():
                if not cfg.get("enabled", True):
                    continue

                if name == "CodeReview":
                    self.analyzers.append(
                        LineLengthAnalyzer(
                            name="CodeReview",
                            threshold=cfg["threshold"],
                            severity="LOW",
                            message="File exceeds 300 lines",
                        )
                    )
                elif name == "ArchitectureReview":
                    self.analyzers.append(
                        LineLengthAnalyzer(
                            name="ArchitectureReview",
                            threshold=cfg["threshold"],
                            severity="MEDIUM",
                            message="Large file detected (>500 lines)",
                        )
                    )
                elif name == "PerformanceReview":
                    self.analyzers.append(
                        LineLengthAnalyzer(
                            name="PerformanceReview",
                            threshold=cfg["threshold"],
                            severity="MEDIUM",
                            message="Large file may impact maintainability",
                        )
                    )
                elif name == "SecurityReview":
                    self.analyzers.append(SecurityReviewAnalyzer())
                elif name == "MLReview":
                    self.analyzers.append(MLReviewAnalyzer())
                elif name == "DependencyReview":
                    self.analyzers.append(DependencyReviewAnalyzer())

    def run(self):
        import ast
        import inspect

        findings = []

        python_files = self.scanner.get_python_files()
        all_files = list(python_files)
        req_path = self.project_path / "requirements.txt"
        if req_path.exists():
            all_files.append(req_path)

        # Check signature once per analyzer to ensure backward compatibility
        analyzer_signatures = {}
        for analyzer in self.analyzers:
            try:
                sig = inspect.signature(analyzer.analyze)
                has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
                supports_di = "content" in sig.parameters or has_kwargs
            except (AttributeError, ValueError):
                supports_di = False
            analyzer_signatures[analyzer] = supports_di

        def analyze_single_file(file_path):
            """Worker task: reads, parses, and analyzes a single file path.

            This function is designed to be thread-safe as each task works on its own
            isolated local variables, ensuring no unsafe shared mutable state.
            """
            file_str = str(file_path)
            file_findings = []

            # Isolated exception handling: if a worker encounters an error (e.g. PermissionError,
            # custom analyzer crash), it is isolated here to prevent terminating the entire run.
            try:
                content = None
                lines = None
                ast_tree = None

                try:
                    with open(file_str, "r", encoding="utf-8") as f:
                        content = f.read()
                    lines = content.splitlines(keepends=True)
                except (FileNotFoundError, PermissionError, UnicodeDecodeError):
                    pass

                if content is not None:
                    try:
                        ast_tree = ast.parse(content)
                    except SyntaxError:
                        pass

                is_requirements = Path(file_path).name == "requirements.txt"
                for analyzer in self.analyzers:
                    if is_requirements:
                        # Invoke only DependencyReviewAnalyzer on requirements.txt
                        if getattr(analyzer, "name", None) != "DependencyReview":
                            continue
                    else:
                        # Do not invoke DependencyReviewAnalyzer on Python files
                        if getattr(analyzer, "name", None) == "DependencyReview":
                            continue

                    if analyzer_signatures.get(analyzer, False):
                        file_findings.extend(
                            analyzer.analyze(file_str, content=content, lines=lines, ast_tree=ast_tree)
                        )
                    else:
                        file_findings.extend(analyzer.analyze(file_str))
            except Exception as e:
                # Log clearly to stderr/stdout without interrupting the rest of the threads
                print(f"Warning: Worker crashed while scanning {file_str}: {e}")

            return file_str, file_findings

        # Fallback to sequential execution if max_workers is explicitly 1 (the default).
        # Parallel mode is optional. For small repositories or purely CPU-bound workloads
        # on warmed page caches, sequential execution is often faster due to GIL contention
        # and thread pool management overhead. Parallel mode (ThreadPoolExecutor) is beneficial
        # primarily for disk-bound scans where files are read from slow, uncached, or network storage.
        if self.max_workers == 1:
            results = [analyze_single_file(f) for f in all_files]
        else:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                results = list(executor.map(analyze_single_file, all_files))

        # Deterministic sorting: threads complete out-of-order, so we explicitly sort
        # the gathered file results alphabetically by file path to keep order identical.
        results.sort(key=lambda r: r[0])

        # Flatten list of findings
        for _, file_findings in results:
            findings.extend(file_findings)

        return findings


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Project Guardian: Lightweight, modular static code analysis engine.", add_help=True
    )
    parser.add_argument("--version", "-v", action="store_true", help="Show application version and exit.")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # doctor command
    subparsers.add_parser("doctor", help="Run system diagnostics checker.")

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan a repository for findings.")
    scan_parser.add_argument("path", help="Path to the repository to scan.")

    args = parser.parse_args(argv)

    if args.version:
        import importlib.metadata

        try:
            app_version = importlib.metadata.version("project-guardian")
        except Exception:
            app_version = "1.1.0"
        print(f"Project Guardian version {app_version}")
        sys.exit(0)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "doctor":
        checker = DiagnosticsChecker()
        report = checker.run_all()
        status = report["status"]

        print("Project Guardian Diagnostics Report")
        print("====================================")
        print(f"Status: {status.upper()}")
        print(f"OS: {report['results'].get('os', 'Unknown')}")
        print(f"Python Version: {report['results'].get('python_version', 'Unknown')}")
        print(f"App Version: {report['results'].get('app_version', 'Unknown')}")
        print(f"Package Metadata: {'OK' if report['results'].get('package_metadata_ok', False) else 'FALLBACK'}")
        print(f"Analyzer Modules: {'OK' if report['results'].get('analyzers_ok', False) else 'FAILED'}")
        print(f"Config Loading: {'OK' if report['results'].get('config_ok', False) else 'FAILED'}")
        print(f"Temp File Creation/Cleanup: {'OK' if report['results'].get('temp_file_ok', False) else 'FAILED'}")
        print(
            f"Report Directory Writability: {'OK' if report['results'].get('report_dir_writability_ok', False) else 'FAILED'}"
        )
        print(f"Git Executable: {'OK' if report['results'].get('git_ok', False) else 'WARNING'}")
        print(f"Dependencies: {'OK' if report['results'].get('dependencies_ok', False) else 'FAILED'}")

        if report["warnings"]:
            print("\nWarnings:")
            for warning in report["warnings"]:
                print(f"  - {warning}")

        if report["errors"]:
            print("\nErrors:")
            for error in report["errors"]:
                print(f"  - {error}")

        if status == "failed":
            sys.exit(1)
        else:
            sys.exit(0)

    elif args.command == "scan":
        target_path = Path(args.path)
        if not target_path.exists():
            print(f"Error: Path '{target_path}' does not exist.", file=sys.stderr)
            sys.exit(2)
        if not target_path.is_dir():
            print(f"Error: Path '{target_path}' is not a directory.", file=sys.stderr)
            sys.exit(2)

        try:
            guardian = ProjectGuardian(project_path=target_path)
            results = guardian.run()

            print(f"Findings: {len(results)}")
            for finding in results:
                print(finding)

            report_path = Path(guardian.report_path)
            if not report_path.is_absolute():
                report_path = target_path / report_path

            guardian.report_writer.write(results, str(report_path))
            print(f"Report generated: {report_path}")
            sys.exit(0)
        except ConfigurationError as e:
            print(f"Configuration Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
