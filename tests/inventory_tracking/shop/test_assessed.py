"""The shop judges its stock through the one assessment entry point (loot/assess.py at SHOP; design.md §10.4 step 1).
The player, 2026-10-23: "I want to have one place that decides pickups/value".

Gate: fixtures/shop_replay.json, frozen by rca/2026-10-23/scripts/assess_2b_shop.py from 3904 recorded items (65
stock items of three captured stocks, 3839 identified reads judged as a vendor's; offline shop triage, 2026-10-23):
24 buys, 0 differ between the old rule and the entry point. The fixture holds every buy, 15 stock items and 30 passes.
"""

import json
import logging
from pathlib import Path

import pytest

from inventory_tracking.loot import assess
from inventory_tracking.loot.assess import Outcome, shop_priced
from inventory_tracking.loot.facts import from_observation
from inventory_tracking.loot.value import appraise_result
from inventory_tracking.shop import rules, service


FIXTURE = Path(__file__).parent / 'fixtures' / 'shop_replay.json'
ITEMS = json.loads(FIXTURE.read_text())['items']


def old_rule(item) -> bool:
    """The rule before the switch: a priced triage verdict or a reviewed pattern."""
    triage = item['result'].get('triage')
    return service.priced(triage) or bool(rules.match_item(item['observation']))


def test_the_sample_holds_buys_by_price_and_by_pattern_and_passes():
    assert sum(item['new'] == 'buy' for item in ITEMS) == 24
    assert any(item['new'] == 'buy' and not rules.match_item(item['observation']) for item in ITEMS)
    assert any(item['new'] == 'buy' and rules.match_item(item['observation']) for item in ITEMS)
    assert any(item['source'].startswith('stock') for item in ITEMS)
    assert FIXTURE.stat().st_size < 300_000


@pytest.mark.parametrize('item', [pytest.param(item, id=f'{n}-{item["title"]}') for n, item in enumerate(ITEMS)])
def test_the_entry_point_buys_what_the_old_rule_bought(item):
    found = service.shop_assessment(item['observation'], item['result'])
    assert found.outcome.value == item['new'], found.said()
    assert (found.outcome == Outcome.BUY) == old_rule(item), found.said()


def stock(monkeypatch, items):
    monkeypatch.setattr(service, 'decode_stock', lambda _: ([dict(item['observation'], vendor='Anya') for item in
                                                             items], []))  # fmt: skip
    results = {item['observation']['source'].get('unit_id'): item['result'] for item in items}
    return lambda observation: results[observation['source'].get('unit_id')]


def test_the_hits_are_equal_with_the_switch_on_and_off(monkeypatch):
    items = [item for item in ITEMS if item['observation']['source'].get('position')]
    for item in items:
        item['observation']['source'].setdefault('container', {'page': 0})
    retrieve = stock(monkeypatch, items)
    record = {'stock_count': len(items), 'timing': {}}
    on = service.assess(record, retrieve=retrieve)
    monkeypatch.setattr(service, 'ASSESSED', False)
    off = service.assess(record, retrieve=retrieve)
    assert on['hits'] == off['hits']
    assert len(on['hits']) == sum(item['new'] == 'buy' for item in items) > 0


def band(q1, median):
    return {'triage': {'verdict': 'sell', 'reason': 'test', 'band': {'q1_ist': q1, 'median_ist': median, 'sellers': 4}}}


@pytest.mark.parametrize(('q1', 'median', 'target'), [(None, 3.0, True), (None, 2.0, False), (2.0, 9.0, False),
                                                     (3.0, None, True), (None, None, False)])  # fmt: skip
def test_one_price_rule_the_quartile_else_the_median(q1, median, target):
    # 2026-10-23: `priced` read no price for a q1_ist key present with None; `shop_priced` read the median. One rule
    # now: the lower quartile, the median when it is missing or empty (loot/value.py `value_ist` reads a band so too)
    result = band(q1, median)
    assert service.priced(result['triage']) is target
    value = appraise_result(from_observation({'item': {'name': 'Ring'}}), result)
    assert (shop_priced(value) is not None) is target


def test_a_difference_logs_one_shadow_line(monkeypatch, caplog):
    monkeypatch.setattr(assess, 'SHADOW_SAID', set())
    [item] = [item for item in ITEMS if item['new'] == 'buy' and not rules.match_item(item['observation'])][:1]
    item = dict(item, observation=dict(item['observation'], source={'position': [0, 0], 'container': {'page': 0}}))
    monkeypatch.setattr(service, 'decode_stock', lambda _: ([dict(item['observation'], vendor='Anya')], []))
    monkeypatch.setattr(service, 'priced', lambda _triage: False)  # the old rule passes it
    with caplog.at_level(logging.INFO):
        result = service.assess({'stock_count': 1, 'timing': {}}, retrieve=lambda _: item['result'])
    assert [hit['name'] for hit in result['hits']] == [item['observation']['item']['name']]  # the entry point's
    [line] = [r.message for r in caplog.records if 'assess: shop' in r.message]
    assert line.endswith('/ old pass (new decides)')


def test_a_priced_hit_shows_the_triage_headline_and_the_patterns(monkeypatch):
    [item] = [item for item in ITEMS if item['new'] == 'buy' and not rules.match_item(item['observation'])][:1]
    item = dict(item, observation=dict(item['observation'], source={'position': [0, 0], 'container': {'page': 0}}))
    monkeypatch.setattr(service, 'decode_stock', lambda _: ([dict(item['observation'], vendor='Anya')], []))
    monkeypatch.setattr(rules, 'match_item', lambda _: ['+3 Hex: Purge'])
    [hit] = service.assess({'stock_count': 1, 'timing': {}}, retrieve=lambda _: item['result'])['hits']
    from inventory_tracking.appraisal.triage import headline

    assert hit['reasons'] == [headline(item['result']['triage']), '+3 Hex: Purge']
    assert hit['triage'] == item['result']['triage']
