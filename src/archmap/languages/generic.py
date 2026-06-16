"""Regex-based analyzer for non-Python source and structural files.

This is intentionally heuristic: it recognises the common shapes of classes,
functions and imports across many languages without a full parser.
"""

from __future__ import annotations

import re
from typing import List

from .base import AnalyzedFile, FileAnalyzer

# class / struct / interface / enum / type declarations
_CLASS_RE = re.compile(
    r"^\s*(?:export\s+)?(?:public\s+|private\s+|protected\s+|abstract\s+|final\s+|sealed\s+|static\s+)*"
    r"(?:class|struct|interface|enum|trait|protocol)\s+([A-Za-z_]\w*)",
    re.MULTILINE,
)

# Function-ish declarations across languages.
_FUNC_PATTERNS = [
    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)", re.MULTILINE),          # JS/TS
    re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\(", re.MULTILINE),                   # Go
    re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)", re.MULTILINE),                   # Rust
    re.compile(r"^\s*def\s+([A-Za-z_]\w*)", re.MULTILINE),                                          # Ruby
    re.compile(r"^\s*func\s+([A-Za-z_]\w*)\s*\(", re.MULTILINE),                                    # Swift
    re.compile(r"^\s*(?:public|private|protected|internal)?\s*(?:static\s+)?[\w<>\[\],.]+\s+"
               r"([A-Za-z_]\w*)\s*\([^;{]*\)\s*\{", re.MULTILINE),                                  # Java/C#/C-like
    re.compile(r"^\s*(?:export\s+)?const\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
               re.MULTILINE),                                                                       # JS arrow consts
]

# import / require / use / include style statements.
_IMPORT_PATTERNS = [
    re.compile(r"""^\s*import\s+(?:.+?\s+from\s+)?['"]([^'"]+)['"]""", re.MULTILINE),               # JS/TS
    re.compile(r"""^\s*(?:const|let|var)\s+.+?=\s*require\(\s*['"]([^'"]+)['"]\s*\)""", re.MULTILINE),
    re.compile(r"^\s*import\s+(?:\"([^\"]+)\"|([\w./]+))", re.MULTILINE),                           # Go/Java
    re.compile(r"^\s*use\s+([\w:]+)", re.MULTILINE),                                                # Rust/PHP
    re.compile(r"""^\s*(?:require|require_relative)\s+['"]([^'"]+)['"]""", re.MULTILINE),           # Ruby
    re.compile(r"""^\s*#include\s+[<"]([^>"]+)[>"]""", re.MULTILINE),                               # C/C++
]

_COMMENT_PREFIXES = ("//", "#", "--", ";", "*", "/*")


class GenericAnalyzer(FileAnalyzer):
    def analyze(self, text: str, name: str) -> AnalyzedFile:
        result = AnalyzedFile(lines=text.count("\n") + 1 if text else 0)
        lower = name.lower()

        if lower.endswith(".md") or lower.endswith(".rst"):
            result.desc = _markdown_desc(text)
            return result

        if lower.endswith((".yaml", ".yml", ".toml", ".ini", ".cfg", ".env", ".json")):
            result.desc = _leading_comment(text) or _config_summary(text, lower)
            return result

        result.desc = _leading_comment(text)

        classes = _CLASS_RE.findall(text)
        result.classes = _dedup(classes)

        funcs: List[str] = []
        for pat in _FUNC_PATTERNS:
            for m in pat.findall(text):
                funcs.append(m if isinstance(m, str) else next((g for g in m if g), ""))
        result.functions = _dedup([f for f in funcs if f and f not in {"if", "for", "while", "switch", "catch"}])

        imports: List[str] = []
        for pat in _IMPORT_PATTERNS:
            for m in pat.findall(text):
                imports.append(m if isinstance(m, str) else next((g for g in m if g), ""))
        result.imports = _dedup([i for i in imports if i])

        return result


def _dedup(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for it in items:
        if it and it not in seen:
            seen.add(it)
            out.append(it)
    return out


def _leading_comment(text: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#!"):
            continue  # shebang
        stripped = line
        for prefix in ("/**", "/*", "//", "#", "--", ";"):
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix):]
                break
        else:
            return ""  # first non-empty line is code, no doc comment
        cleaned = stripped.strip(" *-/").strip()
        if cleaned:
            return cleaned[:200]
    return ""


def _markdown_desc(text: str) -> str:
    title = ""
    para = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if not title:
                title = line.lstrip("#").strip()
            continue
        if not line.startswith(("![", "[", "|", "```", "<")):
            para = line
            break
    if title and para:
        return f"{title} — {para}"[:200]
    return (title or para)[:200]


def _config_summary(text: str, lower: str) -> str:
    if lower.endswith(".json"):
        return "JSON configuration / data file."
    keys = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            keys.append(line.strip("[]"))
        elif ":" in line and not line.startswith("#"):
            key = line.split(":", 1)[0].strip()
            if key and " " not in key and len(key) < 40:
                keys.append(key)
        if len(keys) >= 6:
            break
    if keys:
        return "Config keys: " + ", ".join(keys[:6])
    return "Configuration file."
