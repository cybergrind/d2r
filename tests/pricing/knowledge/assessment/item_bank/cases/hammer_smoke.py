"""Hammerdin early mercenary Smoke, from the explicit armor early/0 guide entry.

Native resistance/recovery and missile defense remain useful at either ethereal
state; Energy and Weaken charges are not usable mercenary stat priorities.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_starter_tail import smoke_cases


CASES = tuple(smoke_cases(build='blessed-hammer-paladin', player_class='Paladin', prefix='hammer'))
