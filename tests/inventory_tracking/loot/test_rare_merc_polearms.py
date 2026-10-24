"""Rare merc polearms by their Traderie sales (the player, 2026-10-24: "refine it with actual traderie sales", then
"implement both"): the ground leaves a non-ethereal rare of the six bases (loot/assess.py ETHEREAL_ONLY_RARE); the want
rows rare-merc-polearm-eth-* keep an ethereal one with 250%+ ED or 30+ IAS with leech; the rest is dropped as before.
The kept cases are the genuine rare sales of 2026-05..09 (guides/warlock.html, the SHOW Rare Merc Polearms row)."""

from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot.assess import (
    ETHEREAL_ONLY_RARE,
    Assessor,
    CalledCopies,
    FakeAppraiser,
    Look,
    Outcome,
    Price,
    Site,
)
from tests.inventory_tracking.loot.test_valuables import facts_of, ground_facts


CODES = {row['name']: row['code'] for row in metadata()['bases'].values() if row.get('name') in ETHEREAL_ONLY_RARE}
# What the live triage says of these rares: the reviewed eth 200%+ ED pattern, CHECK with no price (2026-10-24)
ASSESSOR = Assessor(FakeAppraiser({}, Price(None, 'check')), CalledCopies(lambda _facts: []))


def drop(base: str, *, ethereal: bool | None, unit: int = 7):
    spec = {'base': base, 'code': CODES[base], 'quality': 'rare', 'ethereal': ethereal, 'size': [2, 4]}
    facts = replace(ground_facts({'item': spec}), unit_id=unit)
    return facts if ethereal is not None else replace(facts, ethereal=None)


def rare(base: str, rolls: dict[str, int], *, ethereal: bool = True):
    spec = {'base': base, 'code': CODES[base], 'quality': 'rare', 'ethereal': ethereal, 'size': [2, 4], 'rolls': rolls}
    return facts_of(spec)


def test_the_six_bases_are_named_in_the_game_data():
    assert set(CODES) == set(ETHEREAL_ONLY_RARE)


@pytest.mark.parametrize('base', ETHEREAL_ONLY_RARE)
def test_a_non_ethereal_rare_merc_polearm_is_left_on_the_ground_even_shown(base):
    facts = drop(base, ethereal=False)
    found = ASSESSOR.assess(facts, Site.GROUND, Look(shown=frozenset({facts.unit_id})))
    assert found.outcome == Outcome.LEAVE, found.said()
    assert 'non-ethereal rare merc polearm' in found.why


@pytest.mark.parametrize('ethereal', [True, None], ids=['ethereal', 'flag-unread'])
def test_an_ethereal_or_unread_rare_merc_polearm_is_still_taken_for_the_field_identify(ethereal):
    facts = drop('Mancatcher', ethereal=ethereal)
    found = ASSESSOR.assess(facts, Site.GROUND, Look(shown=frozenset({facts.unit_id})))
    assert found.outcome == Outcome.PICK, found.said()


ED = ('17:0', '18:0')


def ed(value: int) -> dict[str, int]:
    return dict.fromkeys(ED, value)


SOLD = [  # Traderie Recent Trades, SC/NL/PC/RotW (pulled 2026-10-24): the genuine rares with a rune price
    ('Mancatcher', {**ed(288), '93:0': 40}),  # 2026-05-14, 6 Jah
    ('Thresher', {**ed(404), '93:0': 30, '19:0': 295}),  # 2026-08-24, 15 Jah
    ('Giant Thresher', {**ed(368), '60:0': 5, '19:0': 135}),  # 2026-08-17, 4 Jah
    ('Cryptic Axe', {**ed(82), '93:0': 40, '62:0': 9}),  # 2026-09-23, Sur + Ohm
    ('Colossus Voulge', {'93:0': 30, '60:0': 8, '19:0': 108}),  # 2026-07-04, 10 Jah
]


@pytest.mark.parametrize(('base', 'rolls'), SOLD, ids=[base for base, _ in SOLD])
def test_the_ethereal_rares_that_sold_are_kept_in_the_field_and_the_town(base, rolls):
    facts = rare(base, rolls)
    for site in (Site.FIELD, Site.TOWN):
        found = ASSESSOR.assess(facts, site)
        assert found.outcome == Outcome.KEEP, (site, found.said())
    value = ASSESSOR.appraiser.appraise(facts)
    assert value is not None
    assert {want.id for want in value.wants} & {'rare-merc-polearm-eth-ed', 'rare-merc-polearm-eth-ias-leech'}


DROPPED = [
    ('eth 249% ED, no IAS', {**ed(249), '19:0': 200}, True),
    ('eth 100% ED, 30 IAS, no leech', {**ed(100), '93:0': 30}, True),
    ('eth 20 IAS with leech', {'93:0': 20, '60:0': 8}, True),
    ('non-eth 404% ED, 30 IAS', {**ed(404), '93:0': 30}, False),
    ('non-eth Demon Bite 2026-10-24 16:50', {**ed(87), '19:0': 141, '60:0': 9, '62:0': 9}, False),
]


@pytest.mark.parametrize(('rolls', 'ethereal'), [(r, e) for _, r, e in DROPPED], ids=[i for i, _, _ in DROPPED])
def test_the_rest_is_dropped_in_the_field(rolls, ethereal):
    found = ASSESSOR.assess(rare('Mancatcher', rolls, ethereal=ethereal), Site.FIELD)
    assert found.outcome == Outcome.DROP, found.said()
