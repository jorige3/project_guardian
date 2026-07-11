from pathlib import Path

class FileScanner:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)

    def get_python_files(self):
        excluded = {"venv", "tests", "__pycache__"}

        return [
            file
            for file in self.root_path.rglob("*.py")
            if not any(part in excluded for part in file.parts)
            and not file.name.startswith("temp_")
        ]