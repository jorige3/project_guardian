from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from services.file_scanner import FileScanner
from services.report_writer import ReportWriter
from services.config_manager import load_config_file, Config
from analyzers.security_review import SecurityReviewAnalyzer
from analyzers.ml_review import MLReviewAnalyzer
from analyzers.line_length import LineLengthAnalyzer
from analyzers.dependency_review import DependencyReviewAnalyzer


class ProjectGuardian:

    def __init__(self, project_path=".", scanner=None, analyzers=None, report_writer=None, max_workers=None, config=None):
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
                exclude_patterns=self.config.exclude_patterns
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
                    self.analyzers.append(LineLengthAnalyzer(
                        name="CodeReview",
                        threshold=cfg["threshold"],
                        severity="LOW",
                        message="File exceeds 300 lines"
                    ))
                elif name == "ArchitectureReview":
                    self.analyzers.append(LineLengthAnalyzer(
                        name="ArchitectureReview",
                        threshold=cfg["threshold"],
                        severity="MEDIUM",
                        message="Large file detected (>500 lines)"
                    ))
                elif name == "PerformanceReview":
                    self.analyzers.append(LineLengthAnalyzer(
                        name="PerformanceReview",
                        threshold=cfg["threshold"],
                        severity="MEDIUM",
                        message="Large file may impact maintainability"
                    ))
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
                            analyzer.analyze(
                                file_str,
                                content=content,
                                lines=lines,
                                ast_tree=ast_tree
                            )
                        )
                    else:
                        file_findings.extend(
                            analyzer.analyze(file_str)
                        )
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


if __name__ == "__main__":

    guardian = ProjectGuardian()

    results = guardian.run()

    print(f"Findings: {len(results)}")

    for finding in results:
        print(finding)

    guardian.report_writer.write(results, guardian.report_path)
    print(f"Report generated: {guardian.report_path}")