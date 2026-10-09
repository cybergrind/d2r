"""Whether an ethereal copy can be worth anything at all, by equipment slot.

An ethereal item earns its premium through one of three uses: a mercenary wears it
(no durability loss), a socket takes Zod or an indestructible runeword, or the item
never loses durability in the owner's hands (a caster's weapon). Gloves, boots and
belts fail all three: no mercenary slot, zero sockets, and they wear out when hit.
Every other ethereal-capable slot keeps its use-specific review.
"""

NO_USE_TYPES = frozenset({'glov', 'boot', 'belt'})
REASON = 'Gloves, boots and belts have no mercenary slot, take no sockets and cannot be repaired when ethereal.'
SOURCE = 'third-parties/d2data/json/itemtypes.json'
MARKET_BASIS = 'priced as non-ethereal: ' + REASON


def no_ethereal_use(item_type):
    return item_type in NO_USE_TYPES


def family_of(item):
    family = item.get('family')
    if family is None and item.get('base_code'):
        from inventory_tracking.items.metadata import metadata_generation
        from pricing.triage.adapters import bases_by_code

        family = bases_by_code(metadata_generation()).get(item['base_code'], {}).get('type')
    return family


def market_item(item):
    """The item to price, and why: an ethereal copy with no ethereal use trades as the normal one."""
    if item.get('ethereal') is True and no_ethereal_use(family_of(item)):
        return item | {'ethereal': False}, MARKET_BASIS
    return item, None
