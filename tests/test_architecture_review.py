from analyzers.architecture_review import ArchitectureReviewAnalyzer


def test_architecture_review_runs():

    analyzer = ArchitectureReviewAnalyzer()

    findings = analyzer.analyze("agent.py")

    assert isinstance(findings, list)
