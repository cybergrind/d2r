"""Resolve configured actor modifiers followed by the column key."""

from inventory_tracking.config import InputConfig
from inventory_tracking.models import PotionRequest


def keys_for(config: InputConfig, request: PotionRequest) -> tuple[str, ...]:
    return (*config.bindings[request.actor], config.column_keys[request.item.column])
