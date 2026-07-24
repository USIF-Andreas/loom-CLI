from __future__ import annotations

from typing import Callable

from .roles import ROLE_FACTORIES
from .schema import NodeSpec
from ..config import Config

_REGISTRY: dict[str, Callable] = dict(ROLE_FACTORIES)


def register_role(name: str, factory: Callable[[NodeSpec, Config], Callable]) -> None:
    _REGISTRY[name] = factory


def get_role_factory(name: str):
    try:
        return _REGISTRY[name]
    except KeyError:
        known = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown role '{name}'. Known roles: {known}")
