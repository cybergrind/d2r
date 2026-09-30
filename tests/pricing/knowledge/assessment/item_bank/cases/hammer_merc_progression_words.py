"""Explicit Hammerdin early Lionheart/Temper and mid/end Duress alternatives.

Checked wp-a-builds merc armor early/1, mid/1, end/5 and helmet early/3.
These are progression alternatives, not a claim of complete mercenary survival.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_merc_progression_words import REVIEWS, cases


CASES = (
    *cases(build='blessed-hammer-paladin', player_class='Paladin', prefix='hammer'),
    *cases(
        build='blessed-hammer-paladin',
        player_class='Paladin',
        prefix='hammer-end',
        reviews=(
            (
                'duress',
                'duress-end-merc-resistance-alternative',
                REVIEWS[2][2],
                'Dusk Shroud',
                'Quilted Armor',
            ),
        ),
    ),
)
