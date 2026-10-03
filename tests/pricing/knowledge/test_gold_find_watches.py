from dataclasses import replace
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.value_watch import matching_watches
from pricing.knowledge.valuable import build_watchlist
from tests.pricing.knowledge.assessment.item_bank.models import Item


EXAMPLES = (
    ('warcries-gold', 'Grand Charm', ((188, 34, 1), (79, 0, 30)), 'High'),
    ('sharp-gold', 'Grand Charm', ((22, 0, 8), (19, 0, 49), (79, 0, 30)), 'High'),
    ('lucky-gold', 'Grand Charm', ((80, 0, 12), (79, 0, 40)), 'Medium'),
    ('grand-gold', 'Grand Charm', ((79, 0, 40),), 'Low'),
    ('shimmering-gold', 'Small Charm', (*((s, 0, 5) for s in (39, 41, 43, 45)), (79, 0, 10)), 'High'),
    ('ruby-gold', 'Small Charm', ((39, 0, 11), (79, 0, 10)), 'Medium'),
    ('small-gold', 'Small Charm', ((79, 0, 10),), 'Low'),
)


@pytest.fixture(scope='module')
def watches():
    return build_watchlist(Path.cwd())['rows']


@pytest.mark.parametrize(('watch', 'base', 'stats', 'tier'), EXAMPLES)
def test_gold_find_requires_reviewed_combination(watches, watch, base, stats, tier):
    rows = [r for r in watches if r['details'].get('watch_id') == watch]
    assert len(rows) == 1
    item = Item(base, 'magic', raw_stats=stats, complete=True)
    facts = normalize(item.capture())
    assert matching_watches(rows, facts)[0]['details']['guide_tier'] == tier
    assert not matching_watches(rows, replace(facts, capture_complete=False))
    for key, bounds in rows[0]['details']['native_conditions'].items():
        assert not matching_watches(rows, replace(facts, stats={k: v for k, v in facts.stats.items() if k != key}))
        for value in (bounds['min'] - 1, bounds['max'] + 1):
            altered = {**facts.stats, key: {**facts.stats[key], 'value': value}}
            assert not matching_watches(rows, replace(facts, stats=altered))


def test_combined_watch_precedes_plain_resistance_and_gold(watches):
    item = Item('Small Charm', 'magic', raw_stats=(*((s, 0, 5) for s in (39, 41, 43, 45)), (79, 0, 10)), complete=True)
    matched = matching_watches([r for r in watches if r['kind'] == 'affixed_value_watch'], normalize(item.capture()))
    assert [r['details']['watch_id'] for r in matched] == ['shimmering-gold', 'small-gold', 'plain-res-5']


@pytest.mark.parametrize('change', ['planner_roll', 'guide_link', 'guide_tier'])
def test_gold_source_changes_fail_closed(change):
    import json

    from pricing.knowledge.collectible_watches import GUIDE
    from pricing.knowledge.gold_find_watches import gold_specs
    from pricing.knowledge.plain_resistance_watches import PLANNER

    root = Path.cwd()
    html = (root / GUIDE).read_text()
    planner = json.loads((root / PLANNER).read_text())
    if change == 'planner_roll':
        data = json.loads(planner['data'])
        data['items']['122']['stats']['item_goldbonus'] = 9
        planner['data'] = json.dumps(data)
    elif change == 'guide_link':
        html = html.replace('data-d2planner-id="122"', 'data-d2planner-id="123"')
    else:
        html = html.replace('>High</mark>', '>Low</mark>')

    def read(path):
        return json.dumps(planner) if path == PLANNER else (root / path).read_text()

    with pytest.raises(ValueError, match='Gold-find guide/planner evidence changed'):
        gold_specs(read, html)
