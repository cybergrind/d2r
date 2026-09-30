"""Explicit Hammerdin glove/belt/ring alternatives in the cached guide tables.

Goldwrap IAS is not casting speed. These farming/defensive uses do not establish
a Gold Find priority; native/upgraded bases and low rolls retain intrinsic use.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.berserk_farming_accessories import SPECS, cases


SPECS_FOR_CASTER = tuple(
    (slug, item, tuple(key for key in keys if key != '93:0'), upgrades, variable, maximum)
    for slug, item, keys, upgrades, variable, maximum in SPECS
)
CASES = tuple(
    cases(
        build='blessed-hammer-paladin',
        player_class='Paladin',
        prefix='hammer',
        specs=SPECS_FOR_CASTER,
        excluded=('79:0', '93:0'),
    )
)
