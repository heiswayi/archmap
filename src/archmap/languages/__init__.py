"""Language-specific source analyzers."""

from __future__ import annotations

from typing import Dict, Optional

from .base import AnalyzedFile, FileAnalyzer
from .generic import GenericAnalyzer
from .python_analyzer import PythonAnalyzer

# Map a human language label to display metadata.
LANGUAGE_BY_EXT: Dict[str, str] = {
    ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java",
    ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala",
    ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".swift": "Swift",
    ".m": "Objective-C", ".mm": "Objective-C",
    ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++", ".cxx": "C++",
    ".hpp": "C++", ".hh": "C++",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".ps1": "PowerShell",
    ".vue": "Vue", ".svelte": "Svelte",
    ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML", ".ini": "INI",
    ".cfg": "Config", ".env": "Env",
    ".json": "JSON", ".md": "Markdown", ".rst": "reStructuredText",
    ".sql": "SQL", ".graphql": "GraphQL", ".gql": "GraphQL", ".proto": "Protobuf",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".sass": "Sass", ".less": "Less",
    ".tf": "Terraform", ".dockerfile": "Dockerfile", "": "Config",
}

_PYTHON = PythonAnalyzer()
_GENERIC = GenericAnalyzer()


def language_for(ext: str, name: str) -> str:
    lower = name.lower()
    if lower in ("dockerfile",) or lower.startswith("dockerfile"):
        return "Dockerfile"
    if lower in ("makefile", "gnumakefile"):
        return "Makefile"
    return LANGUAGE_BY_EXT.get(ext, "Text")


def analyzer_for(ext: str) -> FileAnalyzer:
    if ext in (".py", ".pyi"):
        return _PYTHON
    return _GENERIC


__all__ = [
    "AnalyzedFile",
    "FileAnalyzer",
    "GenericAnalyzer",
    "PythonAnalyzer",
    "analyzer_for",
    "language_for",
    "LANGUAGE_BY_EXT",
]
