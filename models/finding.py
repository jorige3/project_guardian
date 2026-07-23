from dataclasses import dataclass


@dataclass
class Finding:
    analyzer: str
    severity: str
    file_path: str
    message: str
