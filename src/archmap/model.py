"""Core data structures shared across the scan/analyze/render pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Component:
    """A single analyzed source file (module, config, script, etc.)."""

    id: str
    name: str                       # file name, e.g. "main.py"
    path: str                       # repo-relative path, e.g. "src/app/main.py"
    layer: str                      # layer id this component was assigned to
    language: str                   # human language label, e.g. "Python"
    emoji: str                      # icon shown in the UI
    desc: str = ""                  # short description (docstring/heading/derived)
    lines: int = 0                  # line count
    size: int = 0                   # bytes
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)        # raw import targets
    internal_deps: List[str] = field(default_factory=list)  # component ids depended upon
    used_by: List[str] = field(default_factory=list)        # component ids that depend on this
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "layer": self.layer,
            "language": self.language,
            "emoji": self.emoji,
            "desc": self.desc,
            "lines": self.lines,
            "classes": self.classes,
            "functions": self.functions,
            "methods": self.methods,
            "imports": self.imports,
            "deps": self.internal_deps,
            "usedBy": self.used_by,
            "notes": self.notes,
        }


@dataclass
class Layer:
    """An architectural layer that groups related components."""

    id: str
    name: str
    icon: str
    color: str
    bg: str
    desc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "color": self.color,
            "bg": self.bg,
            "desc": self.desc,
        }


@dataclass
class TreeNode:
    """A node in the rendered file-system tree."""

    name: str
    is_dir: bool
    path: str = ""
    comp_id: Optional[str] = None       # link to a Component when this is a file
    ext: str = ""
    children: List["TreeNode"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        node: Dict[str, Any] = {
            "name": self.name,
            "dir": self.is_dir,
        }
        if self.path:
            node["path"] = self.path
        if self.comp_id:
            node["comp"] = self.comp_id
        if self.ext:
            node["ext"] = self.ext
        if self.children:
            node["children"] = [c.to_dict() for c in self.children]
        return node


@dataclass
class ProjectMap:
    """The complete analyzed model handed to the renderer."""

    name: str
    root: str
    subtitle: str = ""
    layers: List[Layer] = field(default_factory=list)
    components: List[Component] = field(default_factory=list)
    tree: Optional[TreeNode] = None
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta": {
                "name": self.name,
                "root": self.root,
                "subtitle": self.subtitle,
            },
            "layers": [layer.to_dict() for layer in self.layers],
            "components": [c.to_dict() for c in self.components],
            "tree": self.tree.to_dict() if self.tree else {},
            "stats": self.stats,
        }
