from pathlib import Path
from unittest.mock import patch
from analyzers.line_length import LineLengthAnalyzer


def test_line_length_triggers():
    test_file = Path("temp_line_test.py")
    try:
        # Write 10 lines
        test_file.write_text("\n".join(["line"] * 10))

        # Threshold = 5 (should trigger)
        analyzer = LineLengthAnalyzer(
            name="TestReview",
            threshold=5,
            severity="LOW",
            message="Too many lines"
        )
        findings = analyzer.analyze(str(test_file))
        assert len(findings) == 1
        assert findings[0].analyzer == "TestReview"
        assert findings[0].severity == "LOW"
        assert findings[0].message == "Too many lines"
        assert findings[0].file_path == str(test_file)

    finally:
        if test_file.exists():
            test_file.unlink()


def test_line_length_does_not_trigger():
    test_file = Path("temp_line_test.py")
    try:
        # Write 3 lines
        test_file.write_text("\n".join(["line"] * 3))

        # Threshold = 5 (should not trigger)
        analyzer = LineLengthAnalyzer(
            name="TestReview",
            threshold=5,
            severity="LOW",
            message="Too many lines"
        )
        findings = analyzer.analyze(str(test_file))
        assert len(findings) == 0

    finally:
        if test_file.exists():
            test_file.unlink()


def test_line_length_handles_filenotfound():
    analyzer = LineLengthAnalyzer(
        name="TestReview",
        threshold=5,
        severity="LOW",
        message="Too many lines"
    )
    # File does not exist
    findings = analyzer.analyze("non_existent_file.py")
    assert len(findings) == 0


def test_line_length_handles_unicodedecodeerror():
    test_file = Path("temp_binary_file.py")
    try:
        # Write invalid utf-8 byte sequence to trigger UnicodeDecodeError
        test_file.write_bytes(b"\xff\xfe\xfd\xfc")

        analyzer = LineLengthAnalyzer(
            name="TestReview",
            threshold=5,
            severity="LOW",
            message="Too many lines"
        )
        findings = analyzer.analyze(str(test_file))
        assert len(findings) == 0
    finally:
        if test_file.exists():
            test_file.unlink()


def test_exactly_threshold_300():
    test_file = Path("temp_300_test.py")
    try:
        # Write exactly 300 lines
        test_file.write_text("\n".join(["line"] * 300))

        analyzer = LineLengthAnalyzer(
            name="CodeReview",
            threshold=300,
            severity="LOW",
            message="File exceeds 300 lines"
        )
        findings = analyzer.analyze(str(test_file))
        assert len(findings) == 0  # Should not trigger (only > 300)

    finally:
        if test_file.exists():
            test_file.unlink()


def test_exactly_threshold_500():
    test_file = Path("temp_500_test.py")
    try:
        # Write exactly 500 lines
        test_file.write_text("\n".join(["line"] * 500))

        analyzer = LineLengthAnalyzer(
            name="ArchitectureReview",
            threshold=500,
            severity="MEDIUM",
            message="Large file detected (>500 lines)"
        )
        findings = analyzer.analyze(str(test_file))
        assert len(findings) == 0  # Should not trigger (only > 500)

    finally:
        if test_file.exists():
            test_file.unlink()


def test_empty_file():
    test_file = Path("temp_empty_test.py")
    try:
        # Create empty file
        test_file.touch()

        analyzer = LineLengthAnalyzer(
            name="TestReview",
            threshold=0,  # Threshold = 0, should not trigger since len(lines) is 0 (not > 0)
            severity="LOW",
            message="Too many lines"
        )
        findings = analyzer.analyze(str(test_file))
        assert len(findings) == 0

    finally:
        if test_file.exists():
            test_file.unlink()


def test_line_length_handles_permissionerror():
    analyzer = LineLengthAnalyzer(
        name="TestReview",
        threshold=5,
        severity="LOW",
        message="Too many lines"
    )
    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        findings = analyzer.analyze("any_file.py")
    assert len(findings) == 0
