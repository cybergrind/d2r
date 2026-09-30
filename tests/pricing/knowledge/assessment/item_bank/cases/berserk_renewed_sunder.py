"""Standard Berserk Renewed Black Cleft, using independently reviewed native examples.

Source Charms3 illustrates FHR/life/MDR/MF; those are observed values, not minimum
requirements or generator bounds. Original Black Cleft remains a different item.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_renewed_sunder import cases


CASES = tuple(
    cases(
        roles=('berserk-barbarian-renewed-black-cleft-standard-renewed-sunder',),
        player_class='Barbarian',
        prefix='berserk',
    )
)
