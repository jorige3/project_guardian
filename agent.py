from services.file_scanner import FileScanner
from analyzers.code_review import CodeReviewAnalyzer
from services.report_writer import ReportWriter
from analyzers.security_review import SecurityReviewAnalyzer
from analyzers.performance_review import PerformanceReviewAnalyzer
from analyzers.ml_review import MLReviewAnalyzer
from analyzers.architecture_review import ArchitectureReviewAnalyzer
from models.finding import Finding

class ProjectGuardian:

    def __init__(self, project_path="."):
        self.project_path = project_path
        self.scanner = FileScanner(project_path)

        self.analyzers = [
            CodeReviewAnalyzer(),
            SecurityReviewAnalyzer(),
            ArchitectureReviewAnalyzer(),
            PerformanceReviewAnalyzer(),
            MLReviewAnalyzer(),
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

    writer = ReportWriter()

    writer.write(
        results,
        "reports/project_audit.md"
    )

    print("Report generated: reports/project_audit.md")
    
    
    