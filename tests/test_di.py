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
    fake_findings = [
        Finding(
            analyzer="Fake",
            severity="HIGH",
            file_path="target.py",
            message="Test"
        )
    ]
    fake_analyzer = FakeAnalyzer("Fake", fake_findings)

    # Inject fake scanner and fake analyzer
    guardian = ProjectGuardian(
        scanner=fake_scanner,
        analyzers=[fake_analyzer]
    )
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

    guardian = ProjectGuardian(
        scanner=fake_scanner,
        analyzers=[analyzer1, analyzer2, analyzer3]
    )
    guardian.run()

    # Verify execution order is exactly as supplied: analyzer1, then analyzer2, then analyzer3
    assert execution_log == ["first", "second", "third"]
