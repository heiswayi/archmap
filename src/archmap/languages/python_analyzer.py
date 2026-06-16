"""Python analyzer backed by the standard library `ast` module."""

from __future__ import annotations

import ast
from typing import List

from .base import AnalyzedFile, FileAnalyzer


class PythonAnalyzer(FileAnalyzer):
    def analyze(self, text: str, name: str) -> AnalyzedFile:
        result = AnalyzedFile(lines=text.count("\n") + 1 if text else 0)

        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError):
            # Fall back to a shallow read; keep the docstring-less file usable.
            result.notes.append("Could not parse with Python AST (syntax error).")
            return result

        doc = ast.get_docstring(tree)
        if doc:
            result.desc = _first_sentence(doc)

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                result.classes.append(node.name)
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not sub.name.startswith("_"):
                            result.methods.append(f"{node.name}.{sub.name}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    result.functions.append(node.name)

        result.imports = _collect_imports(tree)
        return result


def _collect_imports(tree: ast.Module) -> List[str]:
    imports: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            prefix = "." * (node.level or 0)
            if not mod and node.level:
                # `from . import x, y` — each name is a sibling submodule.
                for alias in node.names:
                    imports.append(prefix + alias.name)
            else:
                imports.append(prefix + mod)
    # De-dup while keeping order.
    seen = set()
    out = []
    for imp in imports:
        if imp and imp not in seen:
            seen.add(imp)
            out.append(imp)
    return out


def _first_sentence(doc: str) -> str:
    doc = doc.strip().replace("\n", " ")
    for stop in (". ", "! ", "? "):
        idx = doc.find(stop)
        if 0 < idx < 200:
            return doc[: idx + 1].strip()
    return doc[:200].strip()
