from concurrent.futures import ThreadPoolExecutor
from services.file_scanner import FileScanner
from services.report_writer import ReportWriter
from analyzers.security_review import SecurityReviewAnalyzer
from analyzers.ml_review import MLReviewAnalyzer
from analyzers.line_length import LineLengthAnalyzer
from analyzers.dependency_review import DependencyReviewAnalyzer


class ProjectGuardian:

    def __init__(self, project_path=".", scanner=None, analyzers=None, report_writer=None, max_workers=1):
        self.project_path = project_path
        self.scanner = scanner if scanner is not None else FileScanner(project_path)
        self.report_writer = report_writer if report_writer is not None else ReportWriter()

        # Normalize worker count: default to 1 (sequential) as the safe default.
        # Values less than 1 are normalized to 1 to prevent invalid executor sizes.
        if max_workers is not None and max_workers < 1:
            self.max_workers = 1
        else:
            self.max_workers = max_workers

        if analyzers is not None:
            self.analyzers = analyzers
        else:
            self.analyzers = [
                LineLengthAnalyzer(
                    name="CodeReview",
                    threshold=300,
                    severity="LOW",
                    message="File exceeds 300 lines"
                ),
                SecurityReviewAnalyzer(),
                LineLengthAnalyzer(
                    name="ArchitectureReview",
                    threshold=500,
                    severity="MEDIUM",
                    message="Large file detected (>500 lines)"
                ),
                LineLengthAnalyzer(
                    name="PerformanceReview",
                    threshold=300,
                    severity="MEDIUM",
                    message="Large file may impact maintainability"
                ),
                MLReviewAnalyzer(),
                DependencyReviewAnalyzer(),
            ]

    def run(self):
        import ast
        import inspect

        findings = []

        python_files = self.scanner.get_python_files()

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

                for analyzer in self.analyzers:
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
            results = [analyze_single_file(f) for f in python_files]
        else:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                results = list(executor.map(analyze_single_file, python_files))

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