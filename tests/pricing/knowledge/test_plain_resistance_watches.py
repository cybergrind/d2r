from dataclasses import replace
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.value_watch import matching_watches
from pricing.knowledge.valuable import build_watchlist
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.fixture(scope='module')
def rows():
    return [r for r in build_watchlist(Path.cwd())['rows'] if r['details'].get('watch_id', '').startswith('plain-res-')]


@pytest.mark.parametrize(('resistance', 'tier'), [(2, None), (3, 'Low'), (4, 'Medium'), (5, 'High'), (6, None)])
@pytest.mark.parametrize('life', [None, 0, 5, 9, 10])
def test_plain_resistance_guide_bands(rows, resistance, tier, life):
    assert len(rows) == 3
    stats = tuple((s, 0, resistance) for s in (39, 41, 43, 45))
    if life is not None:
        stats += ((7, 0, life * 256),)
    facts = normalize(Item('Small Charm', 'magic', raw_stats=stats, complete=True).capture())
    matched = matching_watches(rows, facts)
    assert [r['details']['guide_tier'] for r in matched] == ([tier] if tier and (life is None or life <= 9) else [])
    assert not matching_watches(rows, replace(facts, capture_complete=False))
    for key in ('39:0', '41:0', '43:0', '45:0'):
        assert not matching_watches(rows, replace(facts, stats={k: v for k, v in facts.stats.items() if k != key}))
    broken = {**facts.stats, '7:0': {'status': 'unresolved', 'value': None}}
    assert not matching_watches(rows, replace(facts, stats=broken))


@pytest.mark.parametrize('change', ['planner_roll', 'guide_link', 'guide_tier'])
def test_plain_resistance_source_changes_fail_closed(change):
    import json

    from pricing.knowledge.collectible_watches import GUIDE
    from pricing.knowledge.plain_resistance_watches import PLANNER, planner_specs

    root = Path.cwd()
    html = (root / GUIDE).read_text()
    planner = json.loads((root / PLANNER).read_text())
    if change == 'planner_roll':
        data = json.loads(planner['data'])
        data['items']['101']['stats']['fireresist'] = 4
        planner['data'] = json.dumps(data)
    elif change == 'guide_link':
        html = html.replace('data-d2planner-id="101"', 'data-d2planner-id="102"')
    else:
        html = html.replace('>High</mark>', '>Low</mark>')

    def read(path):
        return json.dumps(planner) if path == PLANNER else (root / path).read_text()

    with pytest.raises(ValueError, match='guide/planner evidence changed'):
        planner_specs(read, html)
