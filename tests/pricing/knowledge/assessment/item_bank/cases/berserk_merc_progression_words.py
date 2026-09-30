"""Berserk explicit early Lionheart/Temper and mid Duress mercenary alternatives.

Reviewed wp-a-builds merc Body Armor early1/mid1 and Helmet early4. Native
low rolls, legal bases and mercenary stat exclusions share independent examples
with the Abyss cases; no active Prayer aura or full survival is implied.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_merc_progression_words import cases


CASES = tuple(cases(build='berserk-barbarian', player_class='Barbarian', prefix='berserk'))
