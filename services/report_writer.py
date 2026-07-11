from pathlib import Path


class ReportWriteError(OSError):
    """Exception raised when writing the audit report fails."""
    pass


class ReportWriter:

    def write(self, findings, output_path):
        try:
            Path(output_path).parent.mkdir(
                parents=True,
                exist_ok=True
            )
        except OSError as e:
            raise ReportWriteError(f"Failed to create output directory for report at {output_path}: {e}") from e

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("# Project Audit Report\n\n")

                for finding in findings:
                    f.write(
                        f"- [{finding.severity}] "
                        f"{finding.file_path}: "
                        f"{finding.message}\n"
                    )
        except OSError as e:
            raise ReportWriteError(f"Failed to write report to {output_path}: {e}") from e