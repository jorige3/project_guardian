from analyzers.base import BaseAnalyzer
from models.finding import Finding


class MLReviewAnalyzer(BaseAnalyzer):

    def analyze(self, file_path):

        findings = []

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "train_test_split(" not in content and "sklearn" in content:
            findings.append(
                Finding(
                    analyzer="MLReview",
                    severity="MEDIUM",
                    file_path=file_path,
                    message="train_test_split not detected"
                )
            )

        return findings