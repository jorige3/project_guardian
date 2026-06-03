from analyzers.code_review import CodeReviewAnalyzer


def test_code_review_runs():

    analyzer = CodeReviewAnalyzer()

    findings = analyzer.analyze("agent.py")

    assert isinstance(findings, list)