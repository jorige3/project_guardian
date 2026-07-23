from unittest.mock import MagicMock, patch
from agent import ProjectGuardian
from services.file_scanner import FileScanner
from services.report_writer import ReportWriter
from analyzers.base import BaseAnalyzer
from models.finding import Finding


class FakeScanner:
    def __init__(self, files):
        self.files = files

    def get_python_files(self):
        return self.files


class FakeAnalyzer(BaseAnalyzer):
    def __init__(self, name, findings):
        self.name = name
        self.findings = findings
        self.executed_files = []

    def analyze(self, file_path: str):
        self.executed_files.append(file_path)
        return self.findings


class FakeReportWriter:
    def __init__(self):
        self.written_findings = None
        self.written_path = None

    def write(self, findings, output_path):
        self.written_findings = findings
        self.written_path = output_path


def test_default_construction():
    guardian = ProjectGuardian()

    # Verify defaults are set correctly
    assert isinstance(guardian.scanner, FileScanner)
    assert isinstance(guardian.report_writer, ReportWriter)
    assert isinstance(guardian.analyzers, list)
    assert len(guardian.analyzers) == 6


def test_inject_fake_scanner():
    fake_files = ["file1.py", "file2.py"]
    fake_scanner = FakeScanner(fake_files)

    # Inject fake scanner
    guardian = ProjectGuardian(scanner=fake_scanner, analyzers=[])
    findings = guardian.run()

    assert findings == []
    # Verify ProjectGuardian used our fake scanner
    assert guardian.scanner is fake_scanner


def test_inject_fake_analyzer():
    fake_scanner = FakeScanner(["target.py"])
    fake_findings = [Finding(analyzer="Fake", severity="HIGH", file_path="target.py", message="Test")]
    fake_analyzer = FakeAnalyzer("Fake", fake_findings)

    # Inject fake scanner and fake analyzer
    guardian = ProjectGuardian(scanner=fake_scanner, analyzers=[fake_analyzer])
    findings = guardian.run()

    assert findings == fake_findings
    assert fake_analyzer.executed_files == ["target.py"]


def test_inject_fake_report_writer():
    fake_writer = FakeReportWriter()

    # Inject fake report writer
    guardian = ProjectGuardian(report_writer=fake_writer)
    assert guardian.report_writer is fake_writer

    test_findings = ["finding1", "finding2"]
    guardian.report_writer.write(test_findings, "output.md")

    assert fake_writer.written_findings == test_findings
    assert fake_writer.written_path == "output.md"


def test_analyzer_execution_order():
    fake_scanner = FakeScanner(["test.py"])

    execution_log = []

    class LoggingAnalyzer(BaseAnalyzer):
        def __init__(self, label):
            self.label = label

        def analyze(self, file_path):
            execution_log.append(self.label)
            return []

    analyzer1 = LoggingAnalyzer("first")
    analyzer2 = LoggingAnalyzer("second")
    analyzer3 = LoggingAnalyzer("third")

    guardian = ProjectGuardian(scanner=fake_scanner, analyzers=[analyzer1, analyzer2, analyzer3])
    guardian.run()

    # Verify execution order is exactly as supplied: analyzer1, then analyzer2, then analyzer3
    assert execution_log == ["first", "second", "third"]


def test_run_with_valid_file(tmp_path):
    test_file = tmp_path / "valid_code.py"
    test_file.write_text("x = 1\ny = 2\n")

    fake_scanner = FakeScanner([str(test_file)])
    guardian = ProjectGuardian(scanner=fake_scanner)
    findings = guardian.run()
    # No findings expected on simple valid assignment code
    assert len(findings) == 0


def test_run_with_invalid_file(tmp_path):
    test_file = tmp_path / "invalid_code.py"
    test_file.write_text("if True x = 1\n")  # SyntaxError

    fake_scanner = FakeScanner([str(test_file)])
    guardian = ProjectGuardian(scanner=fake_scanner)
    findings = guardian.run()
    assert len(findings) == 0


def test_analyzer_signature_inspection_error():
    fake_scanner = FakeScanner(["target.py"])
    bad_analyzer = MagicMock()

    # Mock inspect.signature to raise ValueError
    with patch("inspect.signature", side_effect=ValueError("Invalid signature")):
        guardian = ProjectGuardian(scanner=fake_scanner, analyzers=[bad_analyzer])
        findings = guardian.run()
    assert len(findings) == 0


def test_parallel_concurrency_config():
    # Verify default constructor is sequential (max_workers=1)
    g_default = ProjectGuardian()
    assert g_default.max_workers == 1

    # Verify configurable workers
    g_custom = ProjectGuardian(max_workers=8)
    assert g_custom.max_workers == 8

    # Verify normalization of workers less than 1
    g_zero = ProjectGuardian(max_workers=0)
    assert g_zero.max_workers == 1
    g_neg = ProjectGuardian(max_workers=-5)
    assert g_neg.max_workers == 1


def test_parallel_identical_findings(tmp_path):
    # Setup some python files with line length warnings
    file1 = tmp_path / "a.py"
    file1.write_text("x = 1\n" * 350)  # triggers LineLength > 300

    file2 = tmp_path / "b.py"
    file2.write_text("y = 2\n" * 550)  # triggers LineLength > 500

    fake_scanner = FakeScanner([str(file1), str(file2)])

    # Run sequentially (max_workers=1)
    g_seq = ProjectGuardian(scanner=fake_scanner, max_workers=1)
    findings_seq = g_seq.run()

    # Run in parallel (max_workers=4)
    g_par = ProjectGuardian(scanner=fake_scanner, max_workers=4)
    findings_par = g_par.run()

    # Verify exact equality in findings
    assert len(findings_seq) == len(findings_par)
    for f_seq, f_par in zip(findings_seq, findings_par):
        assert f_seq.analyzer == f_par.analyzer
        assert f_seq.severity == f_par.severity
        assert f_seq.file_path == f_par.file_path
        assert f_seq.message == f_par.message


def test_parallel_deterministic_ordering(tmp_path):
    file_c = tmp_path / "c.py"
    file_c.write_text("x = 1\n" * 350)

    file_a = tmp_path / "a.py"
    file_a.write_text("x = 1\n" * 350)

    # Scanned order is a.py, then c.py (deterministic alphabetically sorted)
    fake_scanner = FakeScanner([str(file_a), str(file_c)])

    g_par = ProjectGuardian(scanner=fake_scanner, max_workers=2)
    findings = g_par.run()

    # Assert findings are ordered alphabetically by file path
    assert len(findings) == 4  # 2 findings per file (CodeReview and PerformanceReview)
    assert findings[0].file_path == str(file_a)
    assert findings[1].file_path == str(file_a)
    assert findings[2].file_path == str(file_c)
    assert findings[3].file_path == str(file_c)


def test_parallel_worker_exception_isolation(tmp_path):
    file1 = tmp_path / "a.py"
    file1.write_text("x = 1\n")

    file2 = tmp_path / "b.py"
    file2.write_text("y = 2\n")

    fake_scanner = FakeScanner([str(file1), str(file2)])

    # Create an analyzer that raises an exception when analyzing "a.py"
    class CrashingAnalyzer(BaseAnalyzer):
        def analyze(self, file_path, content=None, lines=None, ast_tree=None):
            if "a.py" in file_path:
                raise RuntimeError("Crashing on a.py")
            return [Finding("Crashing", "LOW", file_path, "Clean b.py")]

    crashing_analyzer = CrashingAnalyzer()

    # Run parallel
    guardian = ProjectGuardian(scanner=fake_scanner, analyzers=[crashing_analyzer], max_workers=2)

    # The scan should NOT terminate with exception
    findings = guardian.run()

    # It should successfully return the finding for b.py
    assert len(findings) == 1
    assert findings[0].file_path == str(file2)
    assert findings[0].message == "Clean b.py"


def test_parallel_empty_project():
    fake_scanner = FakeScanner([])
    guardian = ProjectGuardian(scanner=fake_scanner, max_workers=4)
    findings = guardian.run()
    assert findings == []


def test_parallel_single_file(tmp_path):
    test_file = tmp_path / "single.py"
    test_file.write_text("x = 1\n" * 350)

    fake_scanner = FakeScanner([str(test_file)])
    guardian = ProjectGuardian(scanner=fake_scanner, max_workers=2)
    findings = guardian.run()
    assert len(findings) == 2


def test_parallel_multiple_files(tmp_path):
    files = []
    for i in range(5):
        f = tmp_path / f"file_{i}.py"
        f.write_text("x = 1\n" * 350)
        files.append(str(f))

    fake_scanner = FakeScanner(files)
    guardian = ProjectGuardian(scanner=fake_scanner, max_workers=4)
    findings = guardian.run()
    assert len(findings) == 10


def test_parallel_large_project_simulation(tmp_path):
    files = []
    for i in range(50):
        f = tmp_path / f"large_{i}.py"
        f.write_text("x = 1\n")
        files.append(str(f))

    fake_scanner = FakeScanner(files)
    guardian = ProjectGuardian(scanner=fake_scanner, max_workers=10)
    findings = guardian.run()
    assert findings == []
