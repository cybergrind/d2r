"""Shared current-generation eligibility for scalar affix comparison proofs.

D2Game ITEMS_RollMagicAffixesNew (ItemsMagic.cpp:311-328) excludes magic-only
rows from rare/crafted items and skips zero-frequency rows. The metadata's base
membership already incorporates item-type inclusion/exclusion. The same native
function computes an affix level clamped to 1..99 before testing row eligibility.
Specific item-level and
coexisting-affix constraints remain the responsibility of each effect proof.
"""

MAX_AFFIX_LEVEL = 99


def can_generate(entry, base_code, rarity):
    definition = entry.get('game_definition', {})
    frequency = definition.get('frequency')
    # Omitted native numeric fields represent zero; retain historical rows for
    # identity decoding, but never use unreachable tiers as generation evidence.
    level = definition.get('level', 0)
    return (
        rarity in ('magic', 'rare', 'crafted')
        and bool(entry.get('spawnable'))
        and base_code in entry.get('base_codes', ())
        and type(frequency) is int
        and frequency > 0
        and type(level) is int
        and 0 <= level <= MAX_AFFIX_LEVEL
        and (rarity == 'magic' or bool(entry.get('rare')))
    )
