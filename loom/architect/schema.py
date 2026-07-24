from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class NodeSpec:
    name: str
    role: str
    provider: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: list[str] = field(default_factory=list)
    max_iterations: int = 1


@dataclass
class EdgeSpec:
    source: str
    target: str
    condition: Optional[str] = None


@dataclass
class ArchitectureSpec:
    name: str
    entry: str
    nodes: list[NodeSpec]
    edges: list[EdgeSpec]
    description: str = ""

    def node(self, name: str) -> NodeSpec:
        for n in self.nodes:
            if n.name == name:
                return n
        raise KeyError(f"Unknown node '{name}' in architecture '{self.name}'")

    def edges_from(self, name: str) -> list[EdgeSpec]:
        return [e for e in self.edges if e.source == name]


def load_architecture(path: str | Path) -> ArchitectureSpec:
    data = yaml.safe_load(Path(path).read_text())

    nodes = [NodeSpec(**n) for n in data.get("nodes", [])]
    edges = [EdgeSpec(**e) for e in data.get("edges", [])]

    spec = ArchitectureSpec(
        name=data["name"],
        entry=data["entry"],
        nodes=nodes,
        edges=edges,
        description=data.get("description", ""),
    )
    _validate(spec)
    return spec


def _validate(spec: ArchitectureSpec) -> None:
    names = {n.name for n in spec.nodes}
    if spec.entry not in names:
        raise ValueError(f"entry '{spec.entry}' is not a defined node")
    for e in spec.edges:
        if e.source not in names:
            raise ValueError(f"edge source '{e.source}' is not a defined node")
        if e.target != "END" and e.target not in names:
            raise ValueError(f"edge target '{e.target}' is not a defined node")
