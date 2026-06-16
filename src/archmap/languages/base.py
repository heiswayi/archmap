"""Base types for language analyzers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class AnalyzedFile:
    """Symbols and metadata extracted from a single source file."""

    desc: str = ""
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    lines: int = 0


class FileAnalyzer:
    """Interface implemented by language-specific analyzers."""

    def analyze(self, text: str, name: str) -> AnalyzedFile:  # pragma: no cover - interface
        raise NotImplementedError
