from pathlib import Path
from analyzers.security_review import SecurityReviewAnalyzer


def test_detects_eval():
    test_file = Path("temp_test.py")
    try:
        test_file.write_text('eval("print(1)")')
        analyzer = SecurityReviewAnalyzer()
        findings = analyzer.analyze(str(test_file))
        assert len(findings) == 1
        assert findings[0].message == "Potential security risk: eval("

    finally:
        if test_file.exists():
            test_file.unlink()


def test_security_false_positives():
    test_file = Path("temp_test.py")
    try:
        # Code with comments and string literals containing the keywords
        code = """
# This is a comment containing eval(
warning_msg = "Please don't use exec( or pickle.loads"
print("Not a call")
"""
        test_file.write_text(code)
        analyzer = SecurityReviewAnalyzer()
        findings = analyzer.analyze(str(test_file))
        # AST should ignore keywords in comments and string literals
        assert len(findings) == 0

    finally:
        if test_file.exists():
            test_file.unlink()


def test_security_syntax_error_fallback():
    test_file = Path("temp_test.py")
    try:
        # Invalid python syntax containing eval(
        code = 'eval("unclosed parenthesis'
        test_file.write_text(code)
        analyzer = SecurityReviewAnalyzer()
        findings = analyzer.analyze(str(test_file))
        # Should fallback to text-based matching and still catch eval(
        assert len(findings) == 1
        assert findings[0].message == "Potential security risk: eval("

    finally:
        if test_file.exists():
            test_file.unlink()


def test_security_resilient_whitespace():
    test_file = Path("temp_test.py")
    try:
        # Valid python code with custom spacing
        code = 'eval   (  "1"  )'
        test_file.write_text(code)
        analyzer = SecurityReviewAnalyzer()
        findings = analyzer.analyze(str(test_file))
        # AST correctly resolves this as a Call node
        assert len(findings) == 1
        assert findings[0].message == "Potential security risk: eval("

    finally:
        if test_file.exists():
            test_file.unlink()