import os
from pathlib import Path


class FileScanner:

    def __init__(self, root_path: str, exclude_dirs=None):
        self.root_path = Path(root_path)
        if exclude_dirs is not None:
            self.exclude_dirs = set(exclude_dirs)
        else:
            self.exclude_dirs = {
                "venv", ".venv", "tests", "__pycache__",
                ".git", ".pytest_cache", "temp_pytest", "node_modules"
            }

    def get_python_files(self):
        python_files = []

        def on_error(err):
            print(f"Warning: Access denied or OS error traversing path: {err.filename} ({err.strerror})")

        try:
            if not self.root_path.exists():
                return []

            # Traverse directory using os.walk
            for dirpath, dirnames, filenames in os.walk(self.root_path, followlinks=False, onerror=on_error):
                pruned_dirs = []
                for d in dirnames:
                    # Ignore hidden directories (starting with '.') or in self.exclude_dirs
                    if d.startswith(".") or d in self.exclude_dirs:
                        continue

                    try:
                        dir_path = Path(dirpath) / d
                        if dir_path.is_symlink() and not dir_path.exists():
                            # Skip broken symlink directories
                            continue
                    except OSError:
                        continue

                    pruned_dirs.append(d)

                # Prune in-place to prevent os.walk from entering skipped directories
                dirnames[:] = pruned_dirs

                for filename in filenames:
                    file_path = Path(dirpath) / filename

                    # Skip broken symlink files
                    try:
                        if file_path.is_symlink() and not file_path.exists():
                            continue
                    except OSError:
                        continue

                    if filename.endswith(".py") and not filename.startswith("temp_"):
                        python_files.append(file_path)

        except OSError as e:
            print(f"Warning: OS error scanning root directory {self.root_path}: {e}")
            return []

        # Return files sorted alphabetically to ensure deterministic ordering
        python_files.sort(key=lambda p: str(p))
        return python_files