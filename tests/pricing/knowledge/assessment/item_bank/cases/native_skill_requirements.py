"""A granted skill can raise the native unique's equip level."""

from dataclasses import replace

from tests.pricing.knowledge.assessment.item_bank.cases.early_unique_baselines import Review, cases


REVIEW = Review(
    'Rusthandle',
    'Grand Scepter',
    16,
    18,
    37,
    0,
    'med',
    'Paladin',
    ((83, 3, 1), (107, 111, 2), (107, 103, 3), (60, 0, 8), (17, 0, 55), (18, 0, 55)),
    ('+1 to Paladin Skill Levels', '+2 (1-3) to Vengeance', '+3 to Thorns', '8% Life stolen per hit', '(50-60%)'),
)


CASES = tuple(
    replace(
        case,
        evidence=(
            *case.evidence,
            'third-parties/d2data/json/skills.json:/111',
            'third-parties/D2MOO/source/D2Common/src/Items/Items.cpp:ITEMS_GetRequiredLevel',
        ),
    )
    for case in cases((REVIEW,), prefix='native-skill-requirements')
)
