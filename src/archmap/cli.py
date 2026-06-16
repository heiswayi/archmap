"""Command-line interface for archmap."""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser

from . import __version__
from .analyzer import build_project_map
from .renderer import write_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="archmap",
        description="Scan a project's source code and generate a single "
                    "interactive architecture-map HTML file.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the project folder to scan (default: current directory).",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output HTML path (default: <project>-architecture.html in the "
             "current directory).",
    )
    parser.add_argument(
        "-n", "--name",
        default=None,
        help="Project name shown in the report (default: folder name).",
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Do not honor the project's .gitignore when scanning.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the generated report in the default web browser.",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output.",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"archmap {__version__}",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        parser.error(f"not a directory: {args.path}")

    def log(msg: str) -> None:
        if not args.quiet:
            print(msg, file=sys.stderr)

    log(f"archmap {__version__} · scanning {root}")
    pmap = build_project_map(root, name=args.name, use_gitignore=not args.no_gitignore)

    if not pmap.components:
        log("No source files found — nothing to map.")
        return 1

    output = args.output or os.path.join(
        os.getcwd(), f"{_safe_name(pmap.name)}-architecture.html"
    )
    write_html(pmap, output)

    s = pmap.stats
    log(f"Analyzed {s['files']} files across {len(pmap.layers)} layers "
        f"({s['edges']} dependency edges).")
    log(f"Wrote {output}")

    if args.open:
        webbrowser.open(f"file://{os.path.abspath(output)}")

    print(output)
    return 0


def _safe_name(name: str) -> str:
    import re
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    return slug or "project"


if __name__ == "__main__":
    raise SystemExit(main())
