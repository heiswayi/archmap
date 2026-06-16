"""Infer architectural layers for components from path/name heuristics."""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

from .model import Layer

# Ordered layer catalogue. Each entry carries the display metadata plus the
# directory keywords and filename hints used to route a file into the layer.
# `dir_kw` matches any path segment; `file_kw` matches the filename stem.
_LAYER_RULES = [
    {
        "id": "entry", "name": "Entry Points", "icon": "🖥️",
        "color": "#1f6feb", "bg": "rgba(31,111,235,0.1)",
        "desc": "CLI entry points, executables, and process launchers.",
        "dir_kw": ["bin", "cmd", "scripts", "script"],
        "file_kw": ["main", "__main__", "cli", "index", "app", "manage",
                    "server", "run", "start", "entrypoint", "wsgi", "asgi"],
    },
    {
        "id": "config", "name": "Config Layer", "icon": "⚙️",
        "color": "#388bfd", "bg": "rgba(56,139,253,0.1)",
        "desc": "Configuration files and settings loaders.",
        "dir_kw": ["config", "configs", "conf", "settings", "configuration"],
        "file_kw": ["config", "settings", "constants", "const", "options", "env"],
        "ext": [".yaml", ".yml", ".toml", ".ini", ".cfg", ".env"],
    },
    {
        "id": "models", "name": "Data Models", "icon": "🗂️",
        "color": "#8957e5", "bg": "rgba(137,87,229,0.1)",
        "desc": "Domain models, schemas, types, and entities.",
        "dir_kw": ["models", "model", "schema", "schemas", "entities", "entity",
                   "domain", "dto", "types", "structs"],
        "file_kw": ["models", "model", "schema", "entity", "types", "type", "dataclass"],
    },
    {
        "id": "api", "name": "API / Routing", "icon": "🌐",
        "color": "#0969da", "bg": "rgba(9,105,218,0.1)",
        "desc": "HTTP routes, controllers, handlers, and views.",
        "dir_kw": ["api", "routes", "route", "router", "controllers", "controller",
                   "handlers", "handler", "views", "endpoints", "resolvers",
                   "graphql", "rest", "rpc"],
        "file_kw": ["routes", "router", "controller", "handler", "view", "urls"],
    },
    {
        "id": "services", "name": "Services / Core", "icon": "⚡",
        "color": "#9e6a03", "bg": "rgba(158,106,3,0.1)",
        "desc": "Business logic, services, and core use-cases.",
        "dir_kw": ["services", "service", "core", "business", "logic", "usecases",
                   "use_cases", "managers", "engine", "processing", "pipeline",
                   "workers", "tasks", "jobs"],
        "file_kw": ["service", "manager", "engine", "processor", "worker"],
    },
    {
        "id": "data", "name": "Data Access", "icon": "💾",
        "color": "#424a53", "bg": "rgba(66,74,83,0.2)",
        "desc": "Databases, repositories, persistence, and migrations.",
        "dir_kw": ["db", "database", "repository", "repositories", "repo", "dao",
                   "store", "stores", "storage", "migrations", "persistence",
                   "queries"],
        "file_kw": ["repository", "database", "models_db", "migration", "dao", "query"],
    },
    {
        "id": "integrations", "name": "Integrations", "icon": "🔌",
        "color": "#6e40c9", "bg": "rgba(110,64,201,0.1)",
        "desc": "External clients, adapters, providers, and connectors.",
        "dir_kw": ["clients", "client", "integrations", "integration", "adapters",
                   "adapter", "providers", "provider", "external", "connectors",
                   "collectors", "collector", "gateways", "llm", "ai"],
        "file_kw": ["client", "adapter", "provider", "connector", "gateway", "collector"],
    },
    {
        "id": "ui", "name": "UI / Frontend", "icon": "🎨",
        "color": "#f778ba", "bg": "rgba(247,120,186,0.1)",
        "desc": "UI components, pages, templates, and styles.",
        "dir_kw": ["components", "component", "ui", "frontend", "pages", "page",
                   "templates", "template", "public", "static", "styles", "style",
                   "assets", "widgets"],
        "file_kw": [],
        "ext": [".vue", ".svelte", ".html", ".css", ".scss", ".sass", ".less"],
    },
    {
        "id": "utils", "name": "Utilities", "icon": "🧰",
        "color": "#39d353", "bg": "rgba(57,211,83,0.1)",
        "desc": "Helpers, shared utilities, and common libraries.",
        "dir_kw": ["utils", "util", "helpers", "helper", "common", "lib", "libs",
                   "shared", "tools", "support"],
        "file_kw": ["utils", "helpers", "helper", "common", "logging", "logger"],
    },
    {
        "id": "tests", "name": "Tests", "icon": "🧪",
        "color": "#3fb950", "bg": "rgba(63,185,80,0.1)",
        "desc": "Unit, integration, and end-to-end tests.",
        "dir_kw": ["tests", "test", "spec", "specs", "__tests__", "e2e", "fixtures"],
        "file_kw": [],
    },
    {
        "id": "docs", "name": "Docs", "icon": "📚",
        "color": "#79c0ff", "bg": "rgba(121,192,255,0.1)",
        "desc": "Documentation and prompts.",
        "dir_kw": ["docs", "doc", "documentation", "prompts", "prompt"],
        "file_kw": ["readme", "changelog", "contributing", "license"],
        "ext": [".md", ".rst"],
    },
    {
        "id": "build", "name": "Build / Ops", "icon": "🛠️",
        "color": "#f0883e", "bg": "rgba(240,136,62,0.1)",
        "desc": "Build, CI/CD, containerization, and infrastructure.",
        "dir_kw": [".github", "ci", "deploy", "deployment", "docker", "k8s",
                   "kubernetes", "helm", "terraform", "infra", "ops", "ansible"],
        "file_kw": ["dockerfile", "makefile", "jenkinsfile", "pyproject",
                    "setup", "package", "build", "gulpfile", "webpack"],
        "ext": [".tf", ".dockerfile"],
    },
]

_MISC = {
    "id": "misc", "name": "Other", "icon": "📦",
    "color": "#8b949e", "bg": "rgba(139,148,163,0.1)",
    "desc": "Files that did not match a specific layer.",
}


def all_layers() -> List[Layer]:
    layers = [
        Layer(id=r["id"], name=r["name"], icon=r["icon"], color=r["color"],
              bg=r["bg"], desc=r["desc"])
        for r in _LAYER_RULES
    ]
    layers.append(Layer(id=_MISC["id"], name=_MISC["name"], icon=_MISC["icon"],
                        color=_MISC["color"], bg=_MISC["bg"], desc=_MISC["desc"]))
    return layers


def classify(rel_path: str, ext: str) -> str:
    """Return the layer id for a file given its relative path and extension."""

    parts = rel_path.lower().split("/")
    dirs = parts[:-1]
    filename = parts[-1]
    stem = os.path.splitext(filename)[0]

    best_id: Optional[str] = None
    best_score = 0

    for rule in _LAYER_RULES:
        score = 0

        # Directory matches are the strongest signal; deeper/closer dirs score
        # slightly higher so a nested "tests/utils" still reads as tests.
        for kw in rule["dir_kw"]:
            if kw in dirs:
                # weight by how specific (later path segment => more local)
                idx = dirs.index(kw)
                score = max(score, 6 + idx)

        # Filename stem hints.
        for kw in rule.get("file_kw", []):
            if stem == kw:
                score = max(score, 5)
            elif kw in stem:
                score = max(score, 3)

        # Extension hints are a weak fallback.
        if ext in rule.get("ext", []):
            score = max(score, 2)

        if score > best_score:
            best_score = score
            best_id = rule["id"]

    return best_id or _MISC["id"]


def _rank_index(layer_id: str) -> int:
    for i, r in enumerate(_LAYER_RULES):
        if r["id"] == layer_id:
            return i
    return len(_LAYER_RULES)
