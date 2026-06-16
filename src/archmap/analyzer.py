"""Tie scanning, language analysis, and layer inference into a ProjectMap."""

from __future__ import annotations

import os
import re
from collections import Counter
from typing import Dict, List, Optional

from . import layers as layer_mod
from .languages import analyzer_for, language_for
from .model import Component, ProjectMap, TreeNode
from .scanner import ScannedFile, scan

# Emoji per language/file kind for the component cards.
_EMOJI_BY_LANG = {
    "Python": "🐍", "JavaScript": "🟨", "TypeScript": "🔷", "Go": "🐹",
    "Rust": "🦀", "Java": "☕", "Kotlin": "🟪", "Ruby": "💎", "PHP": "🐘",
    "C#": "🎯", "Swift": "🦅", "C": "🔧", "C++": "🔧", "Shell": "📜",
    "PowerShell": "📜", "Vue": "💚", "Svelte": "🧡", "YAML": "📋",
    "TOML": "📋", "INI": "📋", "JSON": "🔣", "Markdown": "📝",
    "SQL": "🗄️", "GraphQL": "◈", "Protobuf": "📦", "HTML": "🌐",
    "CSS": "🎨", "SCSS": "🎨", "Dockerfile": "🐳", "Makefile": "🛠️",
    "Terraform": "🏗️",
}


def _slugify(rel_path: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", rel_path.lower()).strip("-")


def build_project_map(root: str, name: Optional[str] = None,
                      use_gitignore: bool = True) -> ProjectMap:
    root = os.path.abspath(root)
    project_name = name or os.path.basename(root.rstrip(os.sep)) or "Project"

    files = scan(root, use_gitignore=use_gitignore)
    components: List[Component] = []
    by_path: Dict[str, Component] = {}

    for sf in files:
        comp = _analyze_file(sf)
        components.append(comp)
        by_path[sf.rel_path] = comp

    _resolve_dependencies(components, by_path)

    pmap = ProjectMap(
        name=project_name,
        root=root,
        subtitle=_make_subtitle(components),
        layers=_used_layers(components),
        components=components,
        tree=_build_tree(project_name, components),
        stats=_build_stats(components),
    )
    return pmap


def _analyze_file(sf: ScannedFile) -> Component:
    try:
        with open(sf.abs_path, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        text = ""

    language = language_for(sf.ext, sf.name)
    analyzed = analyzer_for(sf.ext).analyze(text, sf.name)
    layer_id = layer_mod.classify(sf.rel_path, sf.ext)

    desc = analyzed.desc or _fallback_desc(sf, language, analyzed)
    emoji = _EMOJI_BY_LANG.get(language, "📄")

    return Component(
        id=_slugify(sf.rel_path),
        name=sf.name,
        path=sf.rel_path,
        layer=layer_id,
        language=language,
        emoji=emoji,
        desc=desc,
        lines=analyzed.lines,
        size=sf.size,
        classes=analyzed.classes,
        functions=analyzed.functions,
        methods=analyzed.methods,
        imports=analyzed.imports,
        notes=analyzed.notes,
    )


def _fallback_desc(sf: ScannedFile, language: str, analyzed) -> str:
    bits = []
    if analyzed.classes:
        bits.append(f"{len(analyzed.classes)} class" + ("es" if len(analyzed.classes) != 1 else ""))
    if analyzed.functions:
        bits.append(f"{len(analyzed.functions)} function" + ("s" if len(analyzed.functions) != 1 else ""))
    if bits:
        return f"{language} module — " + ", ".join(bits) + "."
    return f"{language} file."


def _resolve_dependencies(components: List[Component], by_path: Dict[str, Component]) -> None:
    """Best-effort linking of raw imports to in-project components."""

    # Build lookup tables: module-path (dotted), and basename stems.
    dotted_index: Dict[str, Component] = {}
    stem_index: Dict[str, List[Component]] = {}

    for comp in components:
        no_ext = re.sub(r"\.[^./]+$", "", comp.path)
        dotted = no_ext.replace("/", ".")
        dotted_index[dotted] = comp
        # also index without a leading src. / app. style prefix
        parts = dotted.split(".")
        for i in range(len(parts)):
            dotted_index.setdefault(".".join(parts[i:]), comp)
        stem = os.path.splitext(comp.name)[0]
        stem_index.setdefault(stem, []).append(comp)
        # package __init__ resolves to its directory name
        if stem == "__init__":
            pkg = no_ext.rsplit("/", 1)[0].replace("/", ".") if "/" in no_ext else ""
            if pkg:
                dotted_index.setdefault(pkg, comp)

    for comp in components:
        resolved: List[str] = []
        for raw in comp.imports:
            target = _match_import(raw, comp, dotted_index, stem_index)
            if target and target.id != comp.id and target.id not in resolved:
                resolved.append(target.id)
        comp.internal_deps = resolved

    # Reverse edges.
    by_id = {c.id: c for c in components}
    for comp in components:
        for dep_id in comp.internal_deps:
            dep = by_id.get(dep_id)
            if dep and comp.id not in dep.used_by:
                dep.used_by.append(comp.id)


def _match_import(raw: str, comp: Component, dotted_index, stem_index) -> Optional[Component]:
    cleaned = raw.strip()
    if not cleaned:
        return None

    # Path-style relative imports (JS/TS, C includes): they contain a slash.
    if cleaned.startswith(("./", "../", "/")) or ("/" in cleaned and cleaned[0] in "./"):
        target = _resolve_rel_path(cleaned.lstrip("/"), comp)
        if target:
            return _by_path_like(target, dotted_index, stem_index)
        return None

    # Dotted relative python imports (no slash): resolve against the package.
    if cleaned.startswith("."):
        base_parts = comp.path.split("/")[:-1]
        ups = len(cleaned) - len(cleaned.lstrip("."))
        mod = cleaned.lstrip(".")
        anchor = base_parts[: len(base_parts) - (ups - 1)] if ups >= 1 else base_parts
        dotted = ".".join(anchor + (mod.split(".") if mod else []))
        return dotted_index.get(dotted) or _match_stem(mod.split(".")[-1] if mod else "", stem_index)

    # Dotted module path (python/java/go).
    normalized = cleaned.replace("::", ".").replace("/", ".")
    if normalized in dotted_index:
        return dotted_index[normalized]
    # Try progressively shorter suffixes.
    parts = normalized.split(".")
    for i in range(len(parts)):
        cand = ".".join(parts[i:])
        if cand in dotted_index:
            return dotted_index[cand]
    # Last resort: unique basename stem match.
    return _match_stem(parts[-1], stem_index)


def _resolve_rel_path(spec: str, comp: Component) -> Optional[str]:
    base_dir = os.path.dirname(comp.path)
    joined = os.path.normpath(os.path.join(base_dir, spec)).replace(os.sep, "/")
    return joined


def _by_path_like(path_like: str, dotted_index, stem_index) -> Optional[Component]:
    # Drop a trailing source extension (JS imports may keep or omit it) and any
    # explicit /index suffix so "./foo", "./foo.js" and "./foo/index.js" align.
    path_no_ext = re.sub(r"\.[A-Za-z0-9]+$", "", path_like)
    candidates = [path_no_ext]
    if path_no_ext.endswith("/index"):
        candidates.append(path_no_ext[: -len("/index")])
    for cand in candidates:
        dotted = cand.replace("/", ".")
        if dotted in dotted_index:
            return dotted_index[dotted]
    stem = path_no_ext.rsplit("/", 1)[-1]
    return _match_stem(stem, stem_index)


def _match_stem(stem: str, stem_index) -> Optional[Component]:
    if not stem:
        return None
    matches = stem_index.get(stem)
    if matches and len(matches) == 1:
        return matches[0]
    return None


def _used_layers(components: List[Component]):
    present = {c.layer for c in components}
    return [layer for layer in layer_mod.all_layers() if layer.id in present]


def _build_tree(project_name: str, components: List[Component]) -> TreeNode:
    root = TreeNode(name=project_name, is_dir=True, path="")
    dir_nodes: Dict[str, TreeNode] = {"": root}

    for comp in sorted(components, key=lambda c: c.path):
        parts = comp.path.split("/")
        parent = root
        cur_path = ""
        for seg in parts[:-1]:
            cur_path = f"{cur_path}/{seg}" if cur_path else seg
            node = dir_nodes.get(cur_path)
            if node is None:
                node = TreeNode(name=seg, is_dir=True, path=cur_path)
                dir_nodes[cur_path] = node
                parent.children.append(node)
            parent = node
        parent.children.append(
            TreeNode(name=parts[-1], is_dir=False, path=comp.path,
                     comp_id=comp.id, ext=os.path.splitext(comp.name)[1].lstrip("."))
        )

    _sort_tree(root)
    return root


def _sort_tree(node: TreeNode) -> None:
    node.children.sort(key=lambda n: (not n.is_dir, n.name.lower()))
    for child in node.children:
        if child.is_dir:
            _sort_tree(child)


def _build_stats(components: List[Component]) -> Dict:
    lang_counter: Counter = Counter()
    layer_counter: Counter = Counter()
    total_lines = 0
    for c in components:
        lang_counter[c.language] += 1
        layer_counter[c.layer] += 1
        total_lines += c.lines

    languages = [
        {"name": lang, "count": cnt}
        for lang, cnt in lang_counter.most_common()
    ]
    layer_counts = {layer_id: cnt for layer_id, cnt in layer_counter.items()}

    edge_count = sum(len(c.internal_deps) for c in components)

    return {
        "files": len(components),
        "lines": total_lines,
        "languages": languages,
        "layerCounts": layer_counts,
        "edges": edge_count,
        "classes": sum(len(c.classes) for c in components),
        "functions": sum(len(c.functions) + len(c.methods) for c in components),
    }


def _make_subtitle(components: List[Component]) -> str:
    if not components:
        return "No source files found."
    langs = Counter(c.language for c in components)
    top = ", ".join(lang for lang, _ in langs.most_common(3))
    return f"{len(components)} files · {top}"
