from analyzers.performance_review import PerformanceReviewAnalyzer


def test_performance_review_runs():

    analyzer = PerformanceReviewAnalyzer()

    findings = analyzer.analyze("agent.py")

    assert isinstance(findings, list)