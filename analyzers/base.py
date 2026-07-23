from abc import ABC, abstractmethod


class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, file_path: str, content: str = None, lines: list = None, ast_tree=None) -> list:
        pass
