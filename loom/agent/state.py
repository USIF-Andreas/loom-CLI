"""Agent state schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from langchain_core.messages import BaseMessage


@dataclass
class AgentState:
    """State carried through the LangGraph loop."""

    messages: list[BaseMessage] = field(default_factory=list)
    session_id: str = ""
    working_dir: str = "."
    # Set when a tool needs permission and is waiting on the user.
    pending_permission: Optional[dict[str, Any]] = None
    permission_result: str = "allow"  # "allow" | "deny"
