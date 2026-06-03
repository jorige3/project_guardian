from analyzers.security_review import SecurityReviewAnalyzer


def test_detects_eval():

    analyzer = SecurityReviewAnalyzer()

    with open("temp_test.py", "w") as f:
        f.write('eval("print(1)")')

    findings = analyzer.analyze("temp_test.py")

    assert len(findings) == 1