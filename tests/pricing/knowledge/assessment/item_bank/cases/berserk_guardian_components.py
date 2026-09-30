"""Reviewed Harlequin socket components; Berserk does not prioritize magic spell damage.

The variant3 source is Hardcore; the existing reviewed Softcore transfer concerns
this component only, not endorsement of the entire Hardcore setup.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_guardian_components import cases


CASES = tuple(
    cases(
        build='berserk-barbarian',
        player_class='Barbarian',
        prefix='berserk',
        recipients=((1, 'Harlequin Crest', 'Crown of Ages'), (3, 'Harlequin Crest', 'Crown of Ages')),
        keys=('358:0', '85:0', '80:0', '79:0'),
    )
)
