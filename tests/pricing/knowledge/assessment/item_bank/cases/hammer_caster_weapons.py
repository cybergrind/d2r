"""Hammerdin Weapon/2,4,5 alternatives from the reviewed guide table.

Native item definitions establish casting/mana utility. Spell use permits ethereal
Branch/Shard; indestructible Wizardspike cannot spawn ethereal. Attack Rating and
returned damage are not spell bonuses. No source endorsement of Razorswitch.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_caster_unique_alternatives import cases


CASES = tuple(
    cases(
        build='blessed-hammer-paladin',
        player_class='Paladin',
        prefix='hammer',
        suffixes={
            'suicide-branch': 'suicide-branch-caster-progression-alternative',
            'spectral-shard': 'spectral-shard-caster-survival-alternative',
            'wizardspike': 'wizardspike-weapon-utility-alternative',
        },
    )
)
