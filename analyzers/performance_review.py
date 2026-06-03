from analyzers.base import BaseAnalyzer
from models.finding import Finding


class PerformanceReviewAnalyzer(BaseAnalyzer):

    def analyze(self, file_path):

        findings = []

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if len(lines) > 300:
            findings.append(
                Finding(
                    analyzer="PerformanceReview",
                    severity="MEDIUM",
                    file_path=file_path,
                    message="Large file may impact maintainability"
                )
            )

        return findings