"""Shimmering Large and Grand Charms (the player, 2026-10-24: "keep only top rolls for large/grand shimmering"): the top
roll of the top tier (Large 8, Grand 15 all res) is always kept, any suffix (want rows shimmering-*-charm-top); a lower
roll is kept only when its trades price it at 1 Ist or more, so a plain one is dropped (loot/keep.py K7). The prices
are the fill medians of pricing/data/charm-evidence.json (Traderie Recent Trades 2026-09-15..10-24, the guide's
CH-sc-shimmering row)."""

import pytest

from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot.assess import GIVE_UP, Assessor, CalledCopies, FakeAppraiser, Outcome, Price, Site
from inventory_tracking.loot.keep import SHIMMERING_TOP, shimmering_below_top
from tests.inventory_tracking.loot.test_valuables import facts_of


CODES = {
    row['name']: row['code']
    for row in metadata()['bases'].values()
    if row.get('name') in ('Large Charm', 'Grand Charm')
}
SIZES = {'Large Charm': [1, 2], 'Grand Charm': [1, 3]}
RESISTS = ('39:0', '41:0', '43:0', '45:0')
LIFE = '7:0'


def charm(base: str, res: int, unit: int = 3, **suffix: int):
    rolls = {**dict.fromkeys(RESISTS, res), **suffix}
    spec = {'base': base, 'code': CODES[base], 'quality': 'magic', 'size': SIZES[base], 'rolls': rolls}
    return facts_of(spec, unit)


def judged(facts, worth: float | None, verdict: str | None = None, site: Site = Site.TOWN):
    appraiser = FakeAppraiser({facts.unit_id: Price(worth, verdict)}, None)
    return Assessor(appraiser, CalledCopies(lambda _facts: [])).assess(facts, site)


def test_the_top_rolls_are_the_top_tiers_of_the_game_data():
    tiers = {
        row['base_codes'][0]: row['roll_ranges']['39']['max']
        for row in metadata()['affixes']['prefix'].values()
        if row['name'] == 'Shimmering' and row['base_codes'][0] in (CODES['Large Charm'], CODES['Grand Charm'])
    }
    assert (tiers[CODES['Large Charm']], tiers[CODES['Grand Charm']]) == (
        SHIMMERING_TOP['mcha'],
        SHIMMERING_TOP['lcha'],
    )


KEPT = [  # base, all res, suffix, fill median (Ist)
    ('Grand Charm', 15, {}, 1.43),  # 136 trades
    ('Grand Charm', 15, {LIFE: 45 * 256}, 80.0),
    ('Grand Charm', 15, {}, 0.5),  # the top roll is kept whatever its trades say
    ('Large Charm', 8, {}, 0.62),  # 2 priced trades
    ('Large Charm', 8, {'2:0': 3}, 0.62),  # the pinned 8@ + 3 dex
    ('Grand Charm', 14, {LIFE: 44 * 256}, 14.4),  # a lower roll with a fat life suffix: by its trades
    ('Grand Charm', 13, {LIFE: 45 * 256}, 8.23),
]


@pytest.mark.parametrize(('base', 'res', 'suffix', 'worth'), KEPT)
def test_kept_in_the_field_and_the_town(base, res, suffix, worth):
    facts = charm(base, res, **suffix)
    for site in (Site.FIELD, Site.TOWN):
        found = judged(facts, worth, 'sell', site)
        assert found.outcome == Outcome.KEEP, (site, found.said())


DROPPED = [
    ('Grand Charm', 14, 0.79),  # plain, 34 trades
    ('Grand Charm', 13, 0.67),  # plain, 15 trades
    ('Large Charm', 7, 0.2),
    ('Large Charm', 6, 0.67),
]


@pytest.mark.parametrize(('base', 'res', 'worth'), DROPPED)
def test_a_plain_lower_roll_is_sold_in_town_even_over_the_keep_price(base, res, worth):
    facts = charm(base, res)
    sold = judged(facts, worth, 'slow', Site.TOWN)
    assert sold.outcome in GIVE_UP, sold.said()
    assert 'under the top roll' in sold.why
    carried = judged(facts, worth, 'slow', Site.FIELD)  # a charm is never put down in the field: sold at the next town
    assert carried.outcome == Outcome.KEEP, carried.said()


def test_a_lower_roll_with_no_price_is_kept_unknown():
    assert judged(charm('Grand Charm', 14), None).outcome == Outcome.KEEP


@pytest.mark.parametrize(
    ('facts', 'expected'),
    [
        (charm('Grand Charm', 14), 14),
        (charm('Grand Charm', 15), None),
        (charm('Large Charm', 8), None),
        (facts_of({'base': 'Grand Charm', 'code': 'cm3', 'quality': 'magic', 'rolls': {'39:0': 15}}), None),  # Ruby
    ],
    ids=['gc-14', 'gc-15', 'lc-8', 'one-res'],
)
def test_shimmering_below_top(facts, expected):
    assert shimmering_below_top(facts) == expected
