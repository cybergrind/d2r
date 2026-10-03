from dataclasses import replace
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.value_watch import matching_watches
from pricing.knowledge.valuable import build_watchlist
from tests.pricing.knowledge.assessment.item_bank.models import Item


CASES = (
    ('shimmering-balance', 'Small Charm', (*((s, 0, 5) for s in (39, 41, 43, 45)), (99, 0, 5))),
    ('shimmering-inertia', 'Small Charm', (*((s, 0, 5) for s in (39, 41, 43, 45)), (96, 0, 3))),
    ('shimmering-sustenance', 'Small Charm', (*((s, 0, 5) for s in (39, 41, 43, 45)), (7, 0, 3840))),
    ('fine-sustenance', 'Small Charm', ((22, 0, 3), (19, 0, 20), (7, 0, 3840))),
    ('fine-low-life', 'Small Charm', ((22, 0, 3), (19, 0, 20), (7, 0, 2560))),
    ('snake-sustenance', 'Small Charm', ((9, 0, 3072), (7, 0, 3840))),
    ('realgar-fervor', 'Jewel', ((17, 0, 29), (18, 0, 29), (93, 0, 15))),
    ('serpent-life', 'Small Charm', ((9, 0, 4352), (7, 0, 5120))),
    ('scintillating-freedom', 'Jewel', (*((s, 0, 15) for s in (39, 41, 43, 45)), (91, 0, -15))),
    ('scintillating-hope', 'Jewel', (*((s, 0, 15) for s in (39, 41, 43, 45)), (7, 0, 5120))),
    *(
        (f'scintillating-{attribute}', 'Jewel', (*((s, 0, 15) for s in (39, 41, 43, 45)), (stat, 0, 9)))
        for attribute, stat in (('strength', 0), ('dexterity', 2), ('energy', 1))
    ),
    *(
        (f'{element}-good-luck', 'Small Charm', ((stat, 0, 11), (80, 0, 7)))
        for element, stat in (('fire', 39), ('lightning', 41), ('cold', 43), ('poison', 45))
    ),
    *(
        (f'{element}-life', 'Small Charm', ((stat, 0, 11), (7, 0, 5120)))
        for element, stat in (('fire', 39), ('lightning', 41), ('cold', 43), ('poison', 45))
    ),
    ('shimmering-good-luck', 'Small Charm', (*((s, 0, 5) for s in (39, 41, 43, 45)), (80, 0, 7))),
    ('fine-good-luck', 'Small Charm', ((22, 0, 3), (19, 0, 20), (80, 0, 7))),
    ('grand-shimmering-life', 'Grand Charm', (*((s, 0, 15) for s in (39, 41, 43, 45)), (7, 0, 45 * 256))),
    ('grand-shimmering-sustenance', 'Grand Charm', (*((s, 0, 13) for s in (39, 41, 43, 45)), (7, 0, 20 * 256))),
    ('sharp-sustenance', 'Grand Charm', ((22, 0, 8), (19, 0, 49), (7, 0, 20 * 256))),
    ('fine-life', 'Small Charm', ((22, 0, 3), (19, 0, 20), (7, 0, 20 * 256))),
    ('sharp-life', 'Grand Charm', ((22, 0, 10), (19, 0, 76), (7, 0, 45 * 256))),
    ('shimmering-life', 'Small Charm', ((7, 0, 20 * 256), *((s, 0, 5) for s in (39, 41, 43, 45)))),
    ('ruby-fervor', 'Jewel', ((17, 0, 40), (18, 0, 40), (93, 0, 15))),
    ('scintillating-fervor', 'Jewel', (*((s, 0, 15) for s in (39, 41, 43, 45)), (93, 0, 15))),
    ('ruby-fire-fervor', 'Jewel', ((39, 0, 30), (93, 0, 15))),
    ('large-sharp-life', 'Large Charm', ((22, 0, 6), (19, 0, 48), (7, 0, 35 * 256))),
    ('large-shimmering-life', 'Large Charm', (*((s, 0, 8) for s in (39, 41, 43, 45)), (7, 0, 35 * 256))),
)


@pytest.fixture(scope='module')
def watches():
    return build_watchlist(Path(__file__).parents[3])['rows']


def test_shocking_life_requires_both_damage_endpoints_life_and_native_identity(watches):
    rows = [r for r in watches if r.get('details', {}).get('watch_id') == 'shocking-life']
    assert len(rows) == 1
    item = Item(
        'Small Charm',
        'magic',
        raw_stats=((50, 0, 1), (51, 0, 44), (7, 0, 4096)),
        affix_records=(('prefix', 649), ('suffix', 349)),
        complete=True,
    )
    facts = normalize(item.capture())
    assert matching_watches(rows, facts)
    for key, bounds in rows[0]['details']['native_conditions'].items():
        for value in (bounds['min'] - 1, bounds['max'] + 1):
            altered = {**facts.stats, key: {**facts.stats[key], 'value': value}}
            assert not matching_watches(rows, replace(facts, stats=altered))
        assert not matching_watches(rows, replace(facts, stats={k: v for k, v in facts.stats.items() if k != key}))
    for records in (None, (('prefix', 648), ('suffix', 349))):
        assert not matching_watches(rows, normalize(replace(item, affix_records=records).capture()))
    assert not matching_watches(rows, replace(facts, capture_complete=False))


@pytest.mark.parametrize(
    ('watch', 'suffix', 'rate', 'frames'),
    [
        ('pestilent-life', 349, 299, 150),
        ('pestilent-anthrax', 693, 385, 300),
    ],
)
def test_poison_watch_requires_exact_rates_duration_and_affixes(watches, watch, suffix, rate, frames):
    rows = [r for r in watches if r.get('details', {}).get('watch_id') == watch]
    assert len(rows) == 1
    stats = ((57, 0, rate), (58, 0, rate), (59, 0, frames)) + (((7, 0, 5120),) if suffix == 349 else ())
    item = Item(
        'Small Charm', 'magic', raw_stats=stats, affix_records=(('prefix', 661), ('suffix', suffix)), complete=True
    )
    facts = normalize(item.capture())
    assert matching_watches(rows, facts)
    for raw in (None, float(rate), True):
        altered = {**facts.stats, '57:0': {**facts.stats['57:0'], 'raw': raw}}
        assert not matching_watches(rows, replace(facts, stats=altered))
    for stat, _layer, _raw in stats:
        reduced = tuple((s, p, v - 1 if s == stat else v) for s, p, v in stats)
        if stat != 7:
            assert not matching_watches(rows, normalize(replace(item, raw_stats=reduced).capture()))
        assert not matching_watches(
            rows, normalize(replace(item, raw_stats=tuple(r for r in stats if r[0] != stat)).capture())
        )
    assert not matching_watches(rows, normalize(replace(item, affix_records=None).capture()))
    assert not matching_watches(rows, replace(facts, capture_complete=False))


@pytest.mark.parametrize(('watch_id', 'base', 'stats'), CASES)
def test_complete_combinations_match_and_every_required_modifier_matters(watches, watch_id, base, stats):
    rows = [r for r in watches if r.get('details', {}).get('watch_id') == watch_id]
    assert len(rows) == 1
    item = Item(base, 'magic', raw_stats=stats, complete=True)
    facts = normalize(item.capture())
    assert matching_watches(rows, facts)
    assert not matching_watches(rows, replace(facts, capture_complete=False))
    for stat, layer, _ in stats:
        remaining = tuple(r for r in stats if r[:2] != (stat, layer))
        assert not matching_watches(rows, normalize(replace(item, raw_stats=remaining).capture()))
    assert not matching_watches(rows, replace(facts, rarity='rare'))
    for key, bounds in rows[0]['details']['native_conditions'].items():
        for value in (bounds['min'] - 1, bounds['max'] + 1, bounds['min'] + 0.5):
            changed = {**facts.stats, key: {**facts.stats[key], 'value': value}}
            assert not matching_watches(rows, replace(facts, stats=changed))


def test_high_single_roll_does_not_replace_a_combination(watches):
    rows = [r for r in watches if r.get('details', {}).get('watch_id') == 'ruby-fervor']
    assert rows
    for stats in (((17, 0, 36), (18, 0, 36)), ((17, 0, 40), (18, 0, 39), (93, 0, 15))):
        assert not matching_watches(rows, normalize(Item('Jewel', 'magic', raw_stats=stats, complete=True).capture()))


@pytest.mark.parametrize(
    ('watch_id', 'stats', 'prefix'),
    [
        ('rusty-carnage', ((17, 0, 20), (18, 0, 20), (22, 0, 15)), 196),
        ('carbuncle-carnage', ((22, 0, 20),), 183),
    ],
)
def test_low_level_jewel_requires_native_affixes(watches, watch_id, stats, prefix):
    rows = [r for r in watches if r.get('details', {}).get('watch_id') == watch_id]
    assert len(rows) == 1
    item = Item('Jewel', 'magic', raw_stats=stats, affix_records=(('prefix', prefix), ('suffix', 222)), complete=True)
    facts = normalize(item.capture())
    assert matching_watches(rows, facts)
    for key, bounds in rows[0]['details']['native_conditions'].items():
        assert not matching_watches(rows, replace(facts, stats={k: v for k, v in facts.stats.items() if k != key}))
        for value in (bounds['min'] - 1, bounds['max'] + 1):
            altered = {**facts.stats, key: {**facts.stats[key], 'value': value}}
            assert not matching_watches(rows, replace(facts, stats=altered))
    if watch_id == 'rusty-carnage':
        altered = {**facts.stats, '17:0': {**facts.stats['17:0'], 'value': 19}}
        assert not matching_watches(rows, replace(facts, stats=altered))
    for records in (None, (('prefix', 185), ('suffix', 221)), (('prefix', prefix),)):
        assert not matching_watches(rows, normalize(replace(item, affix_records=records).capture()))


def test_damage_ias_value_bands_cross_native_prefix_names_without_gaps(watches):
    rows = [r for r in watches if r.get('details', {}).get('watch_id') in ('realgar-fervor', 'ruby-fervor')]
    for damage, expected in (
        (19, []),
        (20, ['realgar-fervor']),
        (21, ['realgar-fervor']),
        (29, ['realgar-fervor']),
        (30, ['ruby-fervor']),
        (31, ['ruby-fervor']),
        (40, ['ruby-fervor']),
        (41, []),
    ):
        item = Item('Jewel', 'magic', raw_stats=((17, 0, damage), (18, 0, damage), (93, 0, 15)), complete=True)
        assert [r['details']['watch_id'] for r in matching_watches(rows, normalize(item.capture()))] == expected


def test_small_charm_life_bands_do_not_overlap(watches):
    for stats, bands in (
        (
            ((22, 0, 3), (19, 0, 20)),
            {
                4: [],
                5: ['fine-low-life'],
                10: ['fine-low-life'],
                11: ['fine-sustenance'],
                15: ['fine-sustenance'],
                16: ['fine-life'],
                20: ['fine-life'],
                21: [],
            },
        ),
        (
            tuple((s, 0, 5) for s in (39, 41, 43, 45)),
            {
                9: ['plain-res-5'],
                10: ['shimmering-sustenance'],
                15: ['shimmering-sustenance'],
                16: ['shimmering-life'],
                20: ['shimmering-life'],
                21: [],
            },
        ),
    ):
        for life, expected in bands.items():
            item = Item('Small Charm', 'magic', raw_stats=(*stats, (7, 0, life * 256)), complete=True)
            matched = matching_watches(
                [r for r in watches if r.get('kind') == 'affixed_value_watch'], normalize(item.capture())
            )
            assert [r['details']['watch_id'] for r in matched] == expected


@pytest.mark.parametrize(
    ('stats', 'lower', 'upper'),
    [
        (((22, 0, 10), (19, 0, 76)), 'sharp-sustenance', 'sharp-life'),
        (tuple((s, 0, 15) for s in (39, 41, 43, 45)), 'grand-shimmering-sustenance', 'grand-shimmering-life'),
    ],
)
def test_grand_charm_life_bands_have_no_gap_or_duplicate(watches, stats, lower, upper):
    rows = [r for r in watches if r.get('details', {}).get('watch_id') in (lower, upper)]
    for life, expected in ((19, []), (20, [lower]), (29, [lower]), (30, [upper]), (45, [upper]), (46, [])):
        item = Item('Grand Charm', 'magic', raw_stats=(*stats, (7, 0, life * 256)), complete=True)
        matches = matching_watches(rows, normalize(item.capture()))
        assert [r['details']['watch_id'] for r in matches] == expected
