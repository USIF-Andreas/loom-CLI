"""Session data models (lightweight dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Session:
    id: str
    created_at: str
    working_dir: str

    @property
    def created(self) -> datetime:
        from datetime import datetime as dt

        try:
            return dt.fromisoformat(self.created_at)
        except ValueError:
            return datetime.min
