"""Resolve configured actor modifiers followed by the column key."""

from ..config import InputConfig
from ..models import PotionRequest


def keys_for(config: InputConfig, request: PotionRequest) -> tuple[str, ...]:
    return (*config.bindings[request.actor], config.column_keys[request.item.column])
