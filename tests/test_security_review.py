from pathlib import Path

from analyzers.security_review import SecurityReviewAnalyzer


def test_detects_eval():

    test_file = Path("temp_test.py")

    try:
        test_file.write_text('eval("print(1)")')

        analyzer = SecurityReviewAnalyzer()

        findings = analyzer.analyze(str(test_file))

        assert len(findings) == 1

    finally:
        if test_file.exists():
            test_file.unlink()