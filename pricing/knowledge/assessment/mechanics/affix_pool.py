"""Shared current-generation eligibility for scalar affix comparison proofs.

D2Game ITEMS_RollMagicAffixesNew (ItemsMagic.cpp:311-328) excludes magic-only
rows from rare/crafted items and skips zero-frequency rows. The metadata's base
membership already incorporates item-type inclusion/exclusion. Item-level and
coexisting-affix constraints remain the responsibility of each effect proof.
"""


def can_generate(entry, base_code, rarity):
    frequency = entry.get('game_definition', {}).get('frequency')
    return (
        rarity in ('magic', 'rare', 'crafted')
        and bool(entry.get('spawnable'))
        and base_code in entry.get('base_codes', ())
        and type(frequency) is int
        and frequency > 0
        and (rarity == 'magic' or bool(entry.get('rare')))
    )
