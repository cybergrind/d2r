"""The identify card shows what the loop would do with each item, the one assessment entry point at CARD, beside the
verdict (identify/service.py CARD_ASSESSED; loot/assess.py, design.md §10.4 step 4). Display only: the verdict BOOK
holds stays `verdict_for`'s. R3 (rca/2026-10-23/assess-sites-findings.md): a trade value reads TRADE, a vendor sale
VENDOR, never one word for both."""

import json
from pathlib import Path

import pytest

from inventory_tracking.identify import service
from inventory_tracking.identify.service import card_of, item_summary, result_lines
from inventory_tracking.loot import assess, shadow as loot_shadow
from inventory_tracking.loot.assess import NoCopies, TableCopies
from inventory_tracking.loot.facts import Where, from_observation


REPLAY = Path(__file__).parents[1] / 'loot' / 'fixtures' / 'assess_replay.json'
READS = json.loads(REPLAY.read_text())['reads']


@pytest.fixture(autouse=True)
def fresh_shadow(monkeypatch):
    monkeypatch.setattr(assess, 'SHADOW_SAID', set())


def owned(read):
    return None if read['owned'] is None else [from_observation(copy, where=Where.STASH) for copy in read['owned']]


@pytest.mark.parametrize('read', [pytest.param(read, id=f'{n}-{read["title"]}') for n, read in enumerate(READS)])
def test_the_card_says_what_the_town_would_do_and_leaves_the_verdict(read):
    card = card_of(read['observation'], read['result'], TableCopies({}, owned(read)))
    assert card is not None
    assert (card['outcome'] == 'vendor') == (read['expect']['town'] == 'sell'), card
    assert card['rule']
    assert card['why']
    assert item_summary(read['observation'], read['result'])['verdict'] == read['verdict']  # BOOK's input unchanged


def test_a_trade_value_the_town_vendors_reads_trade_and_vendor_never_sell():
    # R3: Raven Frost appraised slow (trade value) and sold by the town as a cheap duplicate (K6)
    read = next(read for read in READS if read['title'] == 'Raven Frost (Ring)')
    card = card_of(read['observation'], read['result'], TableCopies({}, owned(read)))
    assert card is not None
    assert card['outcome'] == 'vendor'
    row = item_summary(
        read['observation'], dict(read['result'], triage={**read['result']['triage'], 'verdict': 'check'})
    )
    row['card'] = card
    texts = [line.text for line in result_lines({'state': 'complete', 'items': [row], 'issues': []})]
    assert any(text.strip().startswith('Loop: VENDOR K6 — ') for text in texts), texts
    assert not any('SELL' in text for text in texts), texts
    slow = item_summary(read['observation'], read['result'])
    assert 'trade' not in result_lines({'state': 'complete', 'items': [slow], 'issues': []})[0].text.split('—')[0]
    assert '0 trade' in result_lines({'state': 'complete', 'items': [slow], 'issues': []})[0].text


def test_a_pass_puts_the_card_beside_the_verdict_and_book_keeps_the_verdict(monkeypatch, tmp_path):
    read = next(read for read in READS if read['title'] == 'Raven Frost (Ring)')
    found = loot_shadow.Book()
    monkeypatch.setattr(loot_shadow, 'BOOK', found)
    monkeypatch.setattr('inventory_tracking.loot.value.CollectionCopies', lambda: TableCopies({}, owned(read)))
    worker = service.IdentifyWorker(
        type('Source', (), {'pid': 1, 'images': {}, 'capture': {}, 'ensure_connected': lambda self: None})(),
        None,
        capture_lock=__import__('threading').Lock(),
        focused=lambda _: True,
        display=lambda _: None,
        output=tmp_path,
        retrieve=lambda _observation: read['result'],
        capture=lambda *args: {},
        decode=lambda record: ([read['observation']], []),
    )
    worker._assess(['1'])
    assert worker.last_result is not None
    [row] = worker.last_result['items']
    assert row['verdict'] == read['verdict']
    assert row['card']['outcome'] == 'vendor'
    entry = found.get(int(read['observation']['source']['unit_id']))
    assert entry is not None
    assert entry.verdict == read['verdict']
    monkeypatch.setattr(service, 'CARD_ASSESSED', False)
    worker._assess(['1'])
    assert worker.last_result is not None
    assert 'card' not in worker.last_result['items'][0]


def test_a_card_that_cannot_be_judged_is_left_out():
    assert card_of({'item': {'name': 'Ring'}}, None, NoCopies()) is not None  # no result: kept (S8), said so

    class Broken:
        def copies(self, facts):
            raise OSError('the collection is gone')

    read = next(read for read in READS if read['title'] == 'Raven Frost (Ring)')
    assert card_of(read['observation'], read['result'], Broken()) is None
