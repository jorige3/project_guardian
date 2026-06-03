from pathlib import Path


class ReportWriter:

    def write(self, findings, output_path):

        Path(output_path).parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(output_path, "w", encoding="utf-8") as f:

            f.write("# Project Audit Report\n\n")

            for finding in findings:

                f.write(
                    f"- [{finding.severity}] "
                    f"{finding.file_path}: "
                    f"{finding.message}\n"
                )