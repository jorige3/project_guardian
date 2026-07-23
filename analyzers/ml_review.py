import ast

from analyzers.base import BaseAnalyzer
from models.finding import Finding


class MLReviewAnalyzer(BaseAnalyzer):
    def analyze(self, file_path, content=None, lines=None, ast_tree=None):

        findings = []

        if content is None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
                print(f"Warning: Skipped ML analysis for {file_path} due to: {e}")
                return []

        try:
            if ast_tree is not None:
                tree = ast_tree
            else:
                tree = ast.parse(content)
            has_sklearn = False
            has_train_test_split = False

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "sklearn" or alias.name.startswith("sklearn."):
                            has_sklearn = True
                elif isinstance(node, ast.ImportFrom):
                    if node.module == "sklearn" or (node.module and node.module.startswith("sklearn.")):
                        has_sklearn = True
                    for alias in node.names:
                        if alias.name == "train_test_split":
                            has_train_test_split = True
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == "train_test_split":
                        has_train_test_split = True
                    elif isinstance(node.func, ast.Attribute) and node.func.attr == "train_test_split":
                        has_train_test_split = True

            if has_sklearn and not has_train_test_split:
                findings.append(
                    Finding(
                        analyzer="MLReview",
                        severity="MEDIUM",
                        file_path=file_path,
                        message="train_test_split not detected",
                    )
                )

        except SyntaxError as e:
            print(
                f"Warning: Syntax error parsing {file_path} for AST analysis. Falling back to text-based matching... Detail: {e}"
            )
            if "train_test_split(" not in content and "sklearn" in content:
                findings.append(
                    Finding(
                        analyzer="MLReview",
                        severity="MEDIUM",
                        file_path=file_path,
                        message="train_test_split not detected",
                    )
                )

        return findings
