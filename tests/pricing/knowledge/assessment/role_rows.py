"""`assess_roles` with its legacy rows typed for tests that index into them."""

from typing import Any

from pricing.knowledge.assessment.profiles import assess_roles


def role_rows(facts, profiles, loadout=None, *, upgrades=None) -> list[dict[str, Any]]:
    """The rows `assess_roles` returns; their values are JSON-like, not the union pyrefly infers from `thaw`."""
    return assess_roles(facts, profiles, loadout, upgrades=upgrades)
