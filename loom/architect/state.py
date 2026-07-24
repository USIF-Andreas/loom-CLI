from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..agent.state import AgentState


@dataclass
class ArchitectState(AgentState):
    plan_path: str = "plan.md"
    route: Optional[str] = None
    review_notes: str = ""
    current_node: str = ""
    iterations: dict = field(default_factory=dict)
