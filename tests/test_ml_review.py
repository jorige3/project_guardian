from analyzers.ml_review import MLReviewAnalyzer


def test_ml_review_runs():

    analyzer = MLReviewAnalyzer()

    with open("temp_ml.py", "w") as f:
        f.write(
            """
from sklearn.linear_model import LinearRegression

model = LinearRegression()
"""
        )

    findings = analyzer.analyze("temp_ml.py")

    assert len(findings) == 1