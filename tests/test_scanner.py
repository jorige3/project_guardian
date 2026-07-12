import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from services.file_scanner import FileScanner


def test_nested_directories(tmp_path):
    dir1 = tmp_path / "dir1"
    dir2 = dir1 / "dir2"
    dir2.mkdir(parents=True)

    file1 = tmp_path / "a.py"
    file2 = dir1 / "b.py"
    file3 = dir2 / "c.py"

    file1.touch()
    file2.touch()
    file3.touch()

    scanner = FileScanner(str(tmp_path))
    files = scanner.get_python_files()

    assert len(files) == 3
    assert files[0] == file1
    assert files[1] == file2
    assert files[2] == file3


def test_ignored_folders(tmp_path):
    venv_dir = tmp_path / "venv"
    node_dir = tmp_path / "node_modules"
    venv_dir.mkdir()
    node_dir.mkdir()

    (venv_dir / "bad.py").touch()
    (node_dir / "bad2.py").touch()

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    valid_file = src_dir / "good.py"
    valid_file.touch()

    scanner = FileScanner(str(tmp_path))
    files = scanner.get_python_files()

    assert len(files) == 1
    assert files[0] == valid_file


def test_hidden_folders(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "ignored.py").touch()

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    valid_file = src_dir / "good.py"
    valid_file.touch()

    scanner = FileScanner(str(tmp_path))
    files = scanner.get_python_files()

    assert len(files) == 1
    assert files[0] == valid_file


def test_empty_directories(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    scanner = FileScanner(str(tmp_path))
    files = scanner.get_python_files()
    assert files == []


def test_deterministic_ordering(tmp_path):
    (tmp_path / "z.py").touch()
    (tmp_path / "a.py").touch()
    (tmp_path / "m.py").touch()

    scanner = FileScanner(str(tmp_path))
    files = scanner.get_python_files()

    assert [f.name for f in files] == ["a.py", "m.py", "z.py"]


def test_permission_error_handling(tmp_path):
    valid_file = tmp_path / "a.py"
    valid_file.touch()

    scanner = FileScanner(str(tmp_path))

    def mock_walk(top, *args, **kwargs):
        yield str(top), ["restricted"], ["a.py"]
        if "onerror" in kwargs and kwargs["onerror"]:
            err = OSError("Permission denied")
            err.filename = "restricted"
            err.strerror = "Permission denied"
            kwargs["onerror"](err)

    with patch("os.walk", side_effect=mock_walk):
        files = scanner.get_python_files()

    assert len(files) == 1
    assert files[0].name == "a.py"


def test_symbolic_links(tmp_path):
    target = tmp_path / "target.py"
    target.touch()

    symlink_file = tmp_path / "link.py"
    symlink_created = False
    try:
        symlink_file.symlink_to(target)
        symlink_created = True
    except OSError:
        pass

    if symlink_created:
        scanner = FileScanner(str(tmp_path))
        files = scanner.get_python_files()
        assert len(files) == 2

        target.unlink()
        files = scanner.get_python_files()
        assert len(files) == 0
    else:
        # Mock is_symlink and exists behavior for broken symlinks
        with patch.object(Path, "is_symlink", return_value=True), \
             patch.object(Path, "exists", return_value=False):

            (tmp_path / "broken_link.py").touch()
            scanner = FileScanner(str(tmp_path))
            files = scanner.get_python_files()
            assert len(files) == 0


def test_root_path_does_not_exist():
    scanner = FileScanner("non_existent_directory_xyz")
    files = scanner.get_python_files()
    assert files == []


def test_custom_exclude_dirs(tmp_path):
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    (custom_dir / "a.py").touch()

    scanner = FileScanner(str(tmp_path), exclude_dirs=["custom"])
    files = scanner.get_python_files()
    assert len(files) == 0


def test_broken_symlink_directory_mocked():
    with patch("services.file_scanner.Path") as mock_path_cls:
        mock_root = MagicMock()
        mock_root.exists.return_value = True
        mock_path_cls.return_value = mock_root

        mock_subdir = MagicMock()
        mock_subdir.is_symlink.return_value = True
        mock_subdir.exists.return_value = False

        mock_root.__truediv__.return_value = mock_subdir

        def mock_walk(top, *args, **kwargs):
            yield str(top), ["broken_dir"], []

        with patch("os.walk", side_effect=mock_walk):
            scanner = FileScanner("dummy")
            files = scanner.get_python_files()
            assert len(files) == 0


def test_broken_symlink_file_mocked():
    with patch("services.file_scanner.Path") as mock_path_cls:
        mock_root = MagicMock()
        mock_root.exists.return_value = True
        mock_path_cls.return_value = mock_root

        mock_file = MagicMock()
        mock_file.is_symlink.return_value = True
        mock_file.exists.return_value = False

        mock_root.__truediv__.return_value = mock_file

        def mock_walk(top, *args, **kwargs):
            yield str(top), [], ["broken_file.py"]

        with patch("os.walk", side_effect=mock_walk):
            scanner = FileScanner("dummy")
            files = scanner.get_python_files()
            assert len(files) == 0


def test_dir_is_symlink_os_error(tmp_path):
    def mock_walk(top, *args, **kwargs):
        yield str(top), ["error_dir"], []

    with patch("os.walk", side_effect=mock_walk), \
         patch.object(Path, "is_symlink", side_effect=OSError("Read error")):

        scanner = FileScanner(str(tmp_path))
        files = scanner.get_python_files()
        assert len(files) == 0


def test_file_is_symlink_os_error(tmp_path):
    def mock_walk(top, *args, **kwargs):
        yield str(top), [], ["error_file.py"]

    with patch("os.walk", side_effect=mock_walk), \
         patch.object(Path, "is_symlink", side_effect=OSError("Read error")):

        scanner = FileScanner(str(tmp_path))
        files = scanner.get_python_files()
        assert len(files) == 0


def test_outer_os_error():
    with patch("os.walk", side_effect=OSError("System error")):
        scanner = FileScanner(".")
        files = scanner.get_python_files()
        assert files == []
