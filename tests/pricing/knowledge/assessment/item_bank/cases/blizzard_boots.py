"""Blizzard boot alternatives at Boots/1..3: Trek, Waterwalk, standalone Aldur."""

from tests.pricing.knowledge.assessment.item_bank.cases.hammer_boots import cases


CASES = tuple(cases(build='blizzard-sorceress', player_class='Sorceress', prefix='blizzard'))
