from analyzers.base import BaseAnalyzer
from models.finding import Finding


class SecurityReviewAnalyzer(BaseAnalyzer):

    SUSPICIOUS_PATTERNS = [
        "eval(",
        "exec(",
        "pickle.loads",
    ]

    def analyze(self, file_path):

        findings = []

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        for pattern in self.SUSPICIOUS_PATTERNS:

            if pattern in content:
                findings.append(
                    Finding(
                        analyzer="SecurityReview",
                        severity="HIGH",
                        file_path=file_path,
                        message=f"Potential security risk: {pattern}"
                    )
                )

        return findings