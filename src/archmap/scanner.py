"""Filesystem walking: decide which files belong to the project source."""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from typing import List, Optional, Set

# Directories that are never part of the architecture of interest.
DEFAULT_IGNORE_DIRS: Set[str] = {
    ".git", ".hg", ".svn",
    "node_modules", "bower_components", "jspm_packages",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".venv", "venv", "env", ".env.d", "virtualenv",
    "dist", "build", "out", "target", "bin.out",
    ".next", ".nuxt", ".svelte-kit", ".angular", ".parcel-cache",
    "coverage", ".nyc_output", "htmlcov",
    ".idea", ".vscode", ".vs", ".gradle", ".cache",
    "vendor", "Pods", "DerivedData",
    "__snapshots__", ".terraform",
}

# File globs that add noise rather than architecture.
DEFAULT_IGNORE_FILES: Set[str] = {
    "*.min.js", "*.min.css", "*.map",
    "*.lock", "package-lock.json", "yarn.lock", "poetry.lock", "pnpm-lock.yaml",
    "*.pyc", "*.pyo", "*.so", "*.o", "*.a", "*.dll", "*.dylib", "*.class",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.ico", "*.webp", "*.bmp",
    "*.pdf", "*.zip", "*.tar", "*.gz", "*.tgz", "*.rar", "*.7z",
    "*.woff", "*.woff2", "*.ttf", "*.eot", "*.otf",
    "*.mp3", "*.mp4", "*.mov", "*.avi", "*.wav",
    "*.db", "*.sqlite", "*.sqlite3",
    ".DS_Store", "Thumbs.db",
}

# Extensions archmap knows how to reason about (source + structural files).
SOURCE_EXTENSIONS: Set[str] = {
    ".py", ".pyi",
    ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx",
    ".go", ".rs", ".java", ".kt", ".kts", ".scala",
    ".rb", ".php", ".cs", ".swift", ".m", ".mm",
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh",
    ".sh", ".bash", ".zsh", ".ps1",
    ".vue", ".svelte",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env",
    ".json", ".md", ".rst",
    ".sql", ".graphql", ".gql", ".proto",
    ".html", ".css", ".scss", ".sass", ".less",
    ".tf", ".dockerfile",
}

# Filenames (no extension or special) that are still meaningful.
SPECIAL_FILENAMES: Set[str] = {
    "dockerfile", "makefile", "rakefile", "gemfile", "procfile",
    "vagrantfile", "jenkinsfile", "brewfile", "caddyfile",
}

MAX_FILE_BYTES = 2_000_000  # skip files larger than ~2 MB


@dataclass
class ScannedFile:
    abs_path: str
    rel_path: str       # posix-style, relative to project root
    name: str
    ext: str            # lowercased extension including dot, or ""
    size: int


class GitignoreMatcher:
    """A deliberately small .gitignore matcher (good enough, not spec-complete)."""

    def __init__(self, patterns: List[str]):
        self.patterns = patterns

    @classmethod
    def from_root(cls, root: str) -> "GitignoreMatcher":
        patterns: List[str] = []
        gi = os.path.join(root, ".gitignore")
        if os.path.isfile(gi):
            try:
                with open(gi, "r", encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if line.startswith("!"):
                            continue  # negations unsupported; ignore them
                        patterns.append(line.rstrip("/"))
            except OSError:
                pass
        return cls(patterns)

    def matches(self, rel_path: str, name: str) -> bool:
        for pat in self.patterns:
            if "/" in pat:
                if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(rel_path, pat + "/*"):
                    return True
            else:
                if fnmatch.fnmatch(name, pat):
                    return True
        return False


def _is_ignored_file(name: str) -> bool:
    lower = name.lower()
    for pat in DEFAULT_IGNORE_FILES:
        if fnmatch.fnmatch(lower, pat):
            return True
    return False


def _classify_ext(name: str) -> Optional[str]:
    lower = name.lower()
    base, ext = os.path.splitext(lower)
    if ext in SOURCE_EXTENSIONS:
        return ext
    if lower in SPECIAL_FILENAMES or base in SPECIAL_FILENAMES:
        return ""  # known special file, treated as extensionless source
    return None


def scan(root: str, use_gitignore: bool = True) -> List[ScannedFile]:
    """Walk *root* and return the source-relevant files."""

    root = os.path.abspath(root)
    gitignore = GitignoreMatcher.from_root(root) if use_gitignore else GitignoreMatcher([])
    results: List[ScannedFile] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored directories in-place so os.walk skips them.
        pruned = []
        for d in dirnames:
            if d in DEFAULT_IGNORE_DIRS or d.endswith(".egg-info"):
                continue
            rel_dir = os.path.relpath(os.path.join(dirpath, d), root).replace(os.sep, "/")
            if gitignore.matches(rel_dir, d):
                continue
            pruned.append(d)
        dirnames[:] = sorted(pruned)

        for fname in sorted(filenames):
            if _is_ignored_file(fname):
                continue
            classified = _classify_ext(fname)
            if classified is None:
                continue
            abs_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(abs_path, root).replace(os.sep, "/")
            if gitignore.matches(rel_path, fname):
                continue
            try:
                size = os.path.getsize(abs_path)
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            results.append(
                ScannedFile(
                    abs_path=abs_path,
                    rel_path=rel_path,
                    name=fname,
                    ext=classified,
                    size=size,
                )
            )

    return results
