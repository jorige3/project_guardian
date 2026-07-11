from pathlib import Path

from analyzers.base import BaseAnalyzer
from models.finding import Finding


class DependencyReviewAnalyzer(BaseAnalyzer):
    name = "DependencyReview"

    def analyze(self, file_path):
        findings = []

        if Path(file_path).name == "requirements.txt":

            content = Path(file_path).read_text(
                encoding="utf-8"
            )

            if "==" not in content:
                findings.append(
                    Finding(
                        analyzer=self.name,
                        severity="LOW",
                        file_path=str(file_path),
                        message="Dependencies are not pinned"
                    )
                )

        return findings