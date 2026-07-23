from unittest.mock import MagicMock
from agent import ProjectGuardian
from analyzers.dependency_review import DependencyReviewAnalyzer
from analyzers.line_length import LineLengthAnalyzer
from analyzers.security_review import SecurityReviewAnalyzer


def test_dependency_review_runs():
    analyzer = DependencyReviewAnalyzer()
    findings = analyzer.analyze("agent.py")
    assert isinstance(findings, list)


def test_requirements_present_and_unpinned(tmp_path):
    # Setup unpinned dependency
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("flask")

    guardian = ProjectGuardian(project_path=str(tmp_path))
    findings = guardian.run()

    # Verify that DependencyReviewAnalyzer was run and detected the unpinned dependency
    dep_findings = [f for f in findings if f.analyzer == "DependencyReview"]
    assert len(dep_findings) == 1
    assert "not pinned" in dep_findings[0].message.lower()


def test_requirements_present_and_fully_pinned(tmp_path):
    # Setup fully pinned dependencies
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("flask==3.0.0\nrequests==2.31.0")

    guardian = ProjectGuardian(project_path=str(tmp_path))
    findings = guardian.run()

    dep_findings = [f for f in findings if f.analyzer == "DependencyReview"]
    assert len(dep_findings) == 0


def test_requirements_missing(tmp_path):
    # No requirements.txt present
    guardian = ProjectGuardian(project_path=str(tmp_path))
    findings = guardian.run()

    dep_findings = [f for f in findings if f.analyzer == "DependencyReview"]
    assert len(dep_findings) == 0


def test_python_findings_plus_dependency_findings_together(tmp_path):
    # Setup unpinned dependency
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("flask")

    # Setup a long python file that triggers LineLengthAnalyzer CodeReview (threshold 300)
    py_file = tmp_path / "large_code.py"
    py_file.write_text("print('hello')\n" * 350)

    guardian = ProjectGuardian(project_path=str(tmp_path))
    findings = guardian.run()

    # Check both LineLength and Dependency findings are present
    assert len(findings) > 1
    analyzers = [f.analyzer for f in findings]
    assert "DependencyReview" in analyzers
    assert "CodeReview" in analyzers

    # Deterministic alphabetical path sorting: large_code.py comes before requirements.txt
    assert str(findings[0].file_path).endswith("large_code.py")
    assert str(findings[-1].file_path).endswith("requirements.txt")


def test_no_duplicate_dependency_findings(tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("flask")

    guardian = ProjectGuardian(project_path=str(tmp_path))

    # Run multiple times to assert no duplication across runs
    findings_1 = guardian.run()
    findings_2 = guardian.run()

    dep_1 = [f.message for f in findings_1 if f.analyzer == "DependencyReview"]
    dep_2 = [f.message for f in findings_2 if f.analyzer == "DependencyReview"]

    assert len(dep_1) == 1
    assert len(dep_2) == 1
    assert dep_1 == dep_2


def test_python_analyzers_never_receive_requirements(tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("flask\n" * 400)  # Long file, would trigger CodeReview if audited

    # Create mock analyzers representing other reviews
    mock_line_length = MagicMock(spec=LineLengthAnalyzer)
    mock_line_length.analyze.return_value = []
    mock_line_length.name = "CodeReview"

    mock_security = MagicMock(spec=SecurityReviewAnalyzer)
    mock_security.analyze.return_value = []
    mock_security.name = "SecurityReview"

    # Use DI to inject these mock analyzers and DependencyReviewAnalyzer
    dep_analyzer = DependencyReviewAnalyzer()
    guardian = ProjectGuardian(project_path=str(tmp_path), analyzers=[mock_line_length, mock_security, dep_analyzer])
    guardian.run()

    # Assert mock analyzers were never invoked with requirements.txt path
    for call in mock_line_length.analyze.call_args_list:
        assert "requirements.txt" not in str(call)
    for call in mock_security.analyze.call_args_list:
        assert "requirements.txt" not in str(call)
