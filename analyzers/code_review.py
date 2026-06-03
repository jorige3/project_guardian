from analyzers.base import BaseAnalyzer
from models.finding import Finding


class CodeReviewAnalyzer(BaseAnalyzer):

    def analyze(self, file_path: str):

        findings = []

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if len(lines) > 300:
            findings.append(
                Finding(
                    analyzer="CodeReview",
                    severity="LOW",
                    file_path=file_path,
                    message="File exceeds 300 lines"
                )
            )

        return findings