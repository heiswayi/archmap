"""Tests for archmap's scanning, layer inference, dependency linking, and render."""

from __future__ import annotations

import json
import os
import re

from archmap import layers
from archmap.analyzer import build_project_map
from archmap.renderer import render


def _write(root, rel, content):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _make_project(tmp_path):
    root = str(tmp_path)
    _write(root, "index.js", "// entry\nimport { r } from './src/api/routes.js';\n")
    _write(root, "src/api/routes.js",
           "// routes\nimport { Svc } from '../services/svc.js';\nexport function r(){}\n")
    _write(root, "src/services/svc.js",
           "// service\nimport { M } from '../models/m.js';\nexport class Svc{}\n")
    _write(root, "src/models/m.js", "// model\nexport class M{}\n")
    _write(root, "src/utils/log.js", "// logger\nexport function log(){}\n")
    _write(root, "config/settings.yaml", "# settings\nport: 8080\n")
    _write(root, "tests/test_svc.js", "// test\nimport { Svc } from '../src/services/svc.js';\n")
    _write(root, "README.md", "# Demo\nA demo project.\n")
    return root


def test_layer_classification():
    assert layers.classify("src/api/routes.js", ".js") == "api"
    assert layers.classify("src/models/user.py", ".py") == "models"
    assert layers.classify("src/services/svc.py", ".py") == "services"
    assert layers.classify("config/settings.yaml", ".yaml") == "config"
    assert layers.classify("tests/test_x.py", ".py") == "tests"
    assert layers.classify("scripts/deploy.sh", ".sh") == "entry"
    assert layers.classify("README.md", ".md") == "docs"
    assert layers.classify("weird/thing.js", ".js") == "misc"


def test_build_and_layers(tmp_path):
    root = _make_project(tmp_path)
    pmap = build_project_map(root, name="Demo")

    assert pmap.name == "Demo"
    assert pmap.stats["files"] == 8
    by_path = {c.path: c for c in pmap.components}
    assert by_path["src/api/routes.js"].layer == "api"
    assert by_path["src/services/svc.js"].layer == "services"
    assert by_path["src/models/m.js"].layer == "models"
    assert by_path["config/settings.yaml"].layer == "config"


def test_dependency_resolution(tmp_path):
    root = _make_project(tmp_path)
    pmap = build_project_map(root, name="Demo")
    by_path = {c.path: c for c in pmap.components}
    id_to_path = {c.id: c.path for c in pmap.components}

    routes = by_path["src/api/routes.js"]
    dep_paths = {id_to_path[d] for d in routes.internal_deps}
    assert "src/services/svc.js" in dep_paths

    svc = by_path["src/services/svc.js"]
    used_by_paths = {id_to_path[u] for u in svc.used_by}
    assert "src/api/routes.js" in used_by_paths
    assert "tests/test_svc.js" in used_by_paths


def test_python_ast_extraction(tmp_path):
    root = str(tmp_path)
    _write(root, "app/core.py",
           '"""Core service module."""\n'
           "import os\n"
           "from .helpers import helper\n\n"
           "class Engine:\n"
           "    def run(self):\n        pass\n\n"
           "def boot():\n    pass\n")
    _write(root, "app/helpers.py", '"""Helpers."""\ndef helper():\n    pass\n')
    pmap = build_project_map(root, name="Py")
    core = {c.path: c for c in pmap.components}["app/core.py"]
    assert "Engine" in core.classes
    assert "boot" in core.functions
    assert "Engine.run" in core.methods
    assert core.desc.startswith("Core service module")
    # relative import resolves to helpers.py
    dep_paths = {next(c.path for c in pmap.components if c.id == d) for d in core.internal_deps}
    assert "app/helpers.py" in dep_paths


def test_render_produces_valid_html(tmp_path):
    root = _make_project(tmp_path)
    pmap = build_project_map(root, name="Demo")
    html = render(pmap)

    assert "<!DOCTYPE html>" in html
    assert "__ARCHMAP_DATA__" not in html
    assert "__ARCHMAP_TITLE__" not in html

    match = re.search(r"const ARCHMAP = (\{.*?\});\n", html, re.DOTALL)
    assert match is not None
    data = json.loads(match.group(1).replace("<\\/", "</"))
    assert data["meta"]["name"] == "Demo"
    assert data["stats"]["files"] == 8
    assert len(data["components"]) == 8
