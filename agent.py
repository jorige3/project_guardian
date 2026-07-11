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

        findings = []

        python_files = self.scanner.get_python_files()

        for file_path in python_files:

            for analyzer in self.analyzers:

                findings.extend(
                    analyzer.analyze(str(file_path))
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
    
    
    