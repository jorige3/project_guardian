from analyzers.base import BaseAnalyzer
from models.finding import Finding


class LineLengthAnalyzer(BaseAnalyzer):

    def __init__(self, name: str, threshold: int, severity: str, message: str):
        self.name = name
        self.threshold = threshold
        self.severity = severity
        self.message = message

    def analyze(self, file_path: str, content: str = None, lines: list = None, ast_tree=None) -> list:
        findings = []
        if lines is None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
                print(f"Warning: Skipped line length analysis for {file_path} due to: {e}")
                return []

        if len(lines) > self.threshold:
            findings.append(
                Finding(
                    analyzer=self.name,
                    severity=self.severity,
                    file_path=file_path,
                    message=self.message
                )
            )

        return findings
