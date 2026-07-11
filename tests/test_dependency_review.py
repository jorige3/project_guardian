from analyzers.dependency_review import DependencyReviewAnalyzer


def test_dependency_review_runs():
    analyzer = DependencyReviewAnalyzer()
    findings = analyzer.analyze("agent.py")

    assert isinstance(findings, list)
