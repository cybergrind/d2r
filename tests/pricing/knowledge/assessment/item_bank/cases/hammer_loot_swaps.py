"""Hammerdin Weapon-Swap Gull/Ali Baba and Off-Hand-Swap Lidless only.

Guide swap slot entries reviewed; main-hand Lidless is not inferred. Native
utility, active-set qualifications and legal upgrades share independent examples.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_loot_shield_alternatives import REVIEWED, cases


REVIEWED_SWAPS = tuple(
    (
        slug,
        item,
        upgrade,
        ('lidless-wall-off-hand-swap-shield-utility-alternative',) if slug == 'lidless' else suffixes,
        keys,
    )
    for slug, item, upgrade, suffixes, keys in REVIEWED
)
CASES = tuple(cases(build='blessed-hammer-paladin', player_class='Paladin', prefix='hammer', reviewed=REVIEWED_SWAPS))
