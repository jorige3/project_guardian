from pathlib import Path


class FileScanner:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)

    def get_python_files(self):
        return [
            file
            for file in self.root_path.rglob("*.py")
            if "venv" not in str(file)
        ]
