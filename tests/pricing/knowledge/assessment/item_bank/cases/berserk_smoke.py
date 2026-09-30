"""Berserk early Smoke: intrinsic resistance utility, not usable mercenary charges."""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_starter_tail import smoke_cases


CASES = tuple(smoke_cases(build='berserk-barbarian', player_class='Barbarian', prefix='berserk'))
