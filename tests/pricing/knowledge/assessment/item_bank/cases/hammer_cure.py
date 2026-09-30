"""Cure is explicitly listed at Hammerdin merc Helmet early/5.

Intrinsic Cleansing and poison mitigation do not require inferred Prayer or
Insight companions. Reviewed against the native Shael/Io/Tal recipe.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.berserk_cure import cases


CASES = tuple(cases(build='blessed-hammer-paladin', player_class='Paladin', prefix='hammer', source_index=5))
