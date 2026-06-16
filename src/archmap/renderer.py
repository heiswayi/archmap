"""Render a ProjectMap into a single self-contained HTML document."""

from __future__ import annotations

import json
import os

from . import __version__
from .model import ProjectMap

_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "template.html")
_DATA_MARKER = "/*__ARCHMAP_DATA__*/{}"
_TITLE_MARKER = "__ARCHMAP_TITLE__"
_VERSION_MARKER = "__ARCHMAP_VERSION__"


def render(pmap: ProjectMap) -> str:
    with open(_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
        template = fh.read()

    data = pmap.to_dict()
    # Embed as JSON; escape "</" so a stray sequence can't close the <script>.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    html = template.replace(_DATA_MARKER, payload)
    html = html.replace(_TITLE_MARKER, _escape_title(pmap.name))
    html = html.replace(_VERSION_MARKER, __version__)
    return html


def _escape_title(name: str) -> str:
    return (
        name.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def write_html(pmap: ProjectMap, output_path: str) -> None:
    html = render(pmap)
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)
