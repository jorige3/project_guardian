from pathlib import Path
from analyzers.ml_review import MLReviewAnalyzer


def test_ml_review_runs():
    test_file = Path("temp_ml.py")
    try:
        analyzer = MLReviewAnalyzer()
        test_file.write_text(
            """
from sklearn.linear_model import LinearRegression
model = LinearRegression()
"""
        )
        findings = analyzer.analyze(str(test_file))
        assert len(findings) == 1

    finally:
        if test_file.exists():
            test_file.unlink()


def test_ml_false_positives():
    test_file = Path("temp_ml.py")
    try:
        # A file with comments or string literals containing sklearn
        # but no actual import. This should NOT trigger an MLReview finding.
        code = """
# We plan to import sklearn in the future
my_string = "sklearn is cool"
"""
        test_file.write_text(code)
        analyzer = MLReviewAnalyzer()
        findings = analyzer.analyze(str(test_file))
        assert len(findings) == 0

    finally:
        if test_file.exists():
            test_file.unlink()


def test_ml_syntax_error_fallback():
    test_file = Path("temp_ml.py")
    try:
        # Syntactically invalid file containing sklearn but no train_test_split
        code = 'import sklearn\nunclosed "string'
        test_file.write_text(code)
        analyzer = MLReviewAnalyzer()
        findings = analyzer.analyze(str(test_file))
        # Should fallback to text matching and raise a finding
        assert len(findings) == 1

    finally:
        if test_file.exists():
            test_file.unlink()


def test_ml_resilient_whitespace():
    test_file = Path("temp_ml.py")
    try:
        # Valid python code with custom spacing around train_test_split
        code = """
import sklearn
from sklearn.model_selection import train_test_split
X_train, X_test = train_test_split   (  [1, 2], test_size=0.5  )
"""
        test_file.write_text(code)
        analyzer = MLReviewAnalyzer()
        findings = analyzer.analyze(str(test_file))
        # Should not raise finding because train_test_split is resolved
        assert len(findings) == 0

    finally:
        if test_file.exists():
            test_file.unlink()
