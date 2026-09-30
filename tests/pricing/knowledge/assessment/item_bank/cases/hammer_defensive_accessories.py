"""Hammerdin main alternatives: Verdungo at Belts/2 and Wisp at Rings/6.

Minimum rolls preserve defensive utility; Wisp's charged spirits are not passive
bonuses. Native minimum/maximum examples are shared independently of role rules.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.berserk_defensive_accessories import cases


CASES = tuple(cases(build='blessed-hammer-paladin', player_class='Paladin', prefix='hammer'))
