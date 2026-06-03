from analyzers.base import BaseAnalyzer
from models.finding import Finding


class ArchitectureReviewAnalyzer(BaseAnalyzer):

    def analyze(self, file_path):

        findings = []

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if len(lines) > 500:
            findings.append(
                Finding(
                    analyzer="ArchitectureReview",
                    severity="MEDIUM",
                    file_path=file_path,
                    message="Large file detected (>500 lines)"
                )
            )

        return findings