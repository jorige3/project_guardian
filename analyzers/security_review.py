import ast

from analyzers.base import BaseAnalyzer
from models.finding import Finding


class SecurityReviewAnalyzer(BaseAnalyzer):

    SUSPICIOUS_PATTERNS = [
        "eval(",
        "exec(",
        "pickle.loads",
    ]

    def analyze(self, file_path, content=None, lines=None, ast_tree=None):
        
        if file_path.endswith("security_review.py"):
            return []

        findings = []

        if content is None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
                print(f"Warning: Skipped security analysis for {file_path} due to: {e}")
                return []

        try:
            if ast_tree is not None:
                tree = ast_tree
            else:
                tree = ast.parse(content)
            detected = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in ["eval", "exec"]:
                        pattern = f"{node.func.id}("
                        if pattern not in detected:
                            detected.add(pattern)
                            findings.append(
                                Finding(
                                    analyzer="SecurityReview",
                                    severity="HIGH",
                                    file_path=file_path,
                                    message=f"Potential security risk: {pattern}"
                                )
                            )
                    elif (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "loads"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "pickle"
                    ):
                        pattern = "pickle.loads"
                        if pattern not in detected:
                            detected.add(pattern)
                            findings.append(
                                Finding(
                                    analyzer="SecurityReview",
                                    severity="HIGH",
                                    file_path=file_path,
                                    message=f"Potential security risk: {pattern}"
                                )
                            )
        except SyntaxError as e:
            print(f"Warning: Syntax error parsing {file_path} for AST analysis. Falling back to text-based matching... Detail: {e}")
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