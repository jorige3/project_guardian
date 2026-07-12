from services.file_scanner import FileScanner
from services.report_writer import ReportWriter
from analyzers.security_review import SecurityReviewAnalyzer
from analyzers.ml_review import MLReviewAnalyzer
from analyzers.line_length import LineLengthAnalyzer
from analyzers.dependency_review import DependencyReviewAnalyzer


class ProjectGuardian:

    def __init__(self, project_path=".", scanner=None, analyzers=None, report_writer=None):
        self.project_path = project_path
        self.scanner = scanner if scanner is not None else FileScanner(project_path)
        self.report_writer = report_writer if report_writer is not None else ReportWriter()

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

        for file_path in python_files:
            file_str = str(file_path)
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
                    findings.extend(
                        analyzer.analyze(
                            file_str,
                            content=content,
                            lines=lines,
                            ast_tree=ast_tree
                        )
                    )
                else:
                    findings.extend(
                        analyzer.analyze(file_str)
                    )

        return findings




if __name__ == "__main__":

    guardian = ProjectGuardian()

    results = guardian.run()

    print(f"Findings: {len(results)}")

    for finding in results:
        print(finding)

    guardian.report_writer.write(
        results,
        "reports/project_audit.md"
    )

    print("Report generated: reports/project_audit.md")
    
    
    