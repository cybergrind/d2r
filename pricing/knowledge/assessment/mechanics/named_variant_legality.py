"""Reject known impossible named variants without treating unknown rolls as invalid."""

from pricing.knowledge.market_mechanics import CATALOGS


# Same reviewed misc families as the offline listing normalizer. Nondurability
# alone is insufficient: upgraded ethereal Phase Blades are a different case.
MISC_BASES = frozenset(name for name, _ in CATALOGS)


def impossible_named_variant(facts, definition):
    if facts.rarity == 'set' and facts.ethereal is True:
        return True
    base = definition.get('base_definition', {})
    if (
        definition.get('base_name') not in MISC_BASES
        or base.get('name') != definition.get('base_name')
        or base.get('code') != facts.base_code
        or base.get('nodurability') != 1
    ):
        return False
    return (
        facts.ethereal is True
        or (type(facts.sockets) is int and facts.sockets != 0)
        or facts.socket_contents == 'filled'
        or bool(facts.socket_items)
    )
