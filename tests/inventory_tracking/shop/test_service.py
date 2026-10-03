import json
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from inventory_tracking.appraisal.service import dispatch, main
from inventory_tracking.shop.service import ShopWorker, result_lines


@pytest.fixture
def worker(tmp_path):
    displays = []
    source = SimpleNamespace(pid=7, images={}, capture={}, ensure_connected=lambda: None)
    with ThreadPoolExecutor(max_workers=1) as executor:
        check = ShopWorker(
            source,
            executor,
            capture_lock=threading.Lock(),
            focused=lambda _: True,
            display=displays.append,
            output=tmp_path,
            clock=lambda: 100,
            capture=lambda *args: {},
            evaluate=lambda _: {
                'state': 'complete',
                'count': 10,
                'stock_count': 10,
                'hits': [],
                'issues': [],
                'vendors': ['Anya'],
                'timing': {},
            },
        )
        yield check, displays, tmp_path


def test_request_cli_and_dispatch(worker, tmp_path):
    check, _, _ = worker
    endpoint = tmp_path / 'socket'
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
        server.bind(str(endpoint))
        server.settimeout(1)
        assert main(['request', '--shop', '--socket', str(endpoint)]) == 0
        assert server.recv(256).startswith(b'shop ')
    assert dispatch(b'shop 100', 100, None, None, check)
    check.future.result(timeout=2)
    assert not dispatch(b'shop nan', 100, None, None, check)
    assert not dispatch(b'shop 98', 100, None, None, check)


def test_fast_async_result_and_osd_expiry(worker):
    check, displays, path = worker
    assert check.request(100, 100)
    check.future.result(timeout=2)
    check.tick()
    assert 'No shopping targets' in displays[-1][0].text
    assert json.loads((path / 'shop-latest.json').read_text())['count'] == 10
    check.clock = lambda: 104.9  # no targets: 5 s lease
    check.tick()
    assert displays[-1] != []
    check.clock = lambda: 105
    check.tick()
    assert displays[-1] == []
    assert check.visible is None


def test_focus_loss_and_superseded_work_cannot_publish_osd(worker):
    check, displays, _ = worker
    started, release = threading.Event(), threading.Event()

    def capture(*args):
        started.set()
        assert release.wait(2)
        return {}

    check.capture = capture
    assert check.request(100, 100)
    assert started.wait(2)
    assert not check.request(101, 101)  # no overlapping memory captures
    check.dismiss()  # an Alt+D request supersedes the scan
    release.set()
    check.future.result(timeout=2)
    check.tick()
    assert not displays
    assert check.visible is None


def test_read_failure_is_visible_and_allows_retry(worker):
    check, displays, _ = worker

    def fail(*args):
        raise ValueError('stock changed')

    check.capture = fail
    assert check.request(100, 100)
    check.future.result(timeout=2)
    check.tick()
    assert displays[-1][0].text == 'Shop check unavailable'
    assert displays[-1][1].text == 'stock changed'
    assert not check.busy


def test_found_names_and_bonuses_are_in_osd():
    lines = result_lines(
        {
            'state': 'complete',
            'count': 30,
            'stock_count': 30,
            'vendors': ['Drognan'],
            'issues': [],
            'hits': [
                {
                    'name': 'Kriss',
                    'vendor': 'Drognan',
                    'page': 1,
                    'position': [2, 3],
                    'reasons': ['+3 Hex: Purge / +3 Eldritch Blast'],
                }
            ],
        }
    )
    assert '1 targets found' in lines[0].text
    assert 'Kriss' in lines[1].text
    assert 'tab 2, (3, 4)' in lines[1].text
    assert 'Hex: Purge' in lines[2].text
    assert 'Eldritch Blast' in lines[2].text


def test_partial_results_preserve_raw_evidence_for_decoder_diagnosis(worker):
    check, displays, path = worker
    check.capture = lambda *args: {'raw_stock': 'retained'}
    check.evaluate = lambda _: {
        'state': 'partial',
        'count': 1,
        'stock_count': 1,
        'hits': [],
        'vendors': ['Fara'],
        'issues': ['unknown stat'],
        'timing': {},
    }
    assert check.request(100, 100)
    check.future.result(timeout=2)
    evidence = json.loads((path / 'shop-diagnostics.json').read_text())
    assert evidence['record'] == {'raw_stock': 'retained'}
    assert evidence['result']['issues'] == ['unknown stat']
    check.tick()
    assert 'incomplete' in displays[-1][0].text


def test_unresolved_stat_issue_identifies_vendor_item_and_native_payload(monkeypatch):
    from inventory_tracking.shop import service

    observation = {
        'item': {'name': 'Amulet'},
        'vendor': 'Larzuk',
        'source': {'unit_id': 3372686176},
        'unresolved_stats': [{'id': 999, 'layer': 12, 'raw': 34}],
    }
    monkeypatch.setattr(service, 'decode_stock', lambda _: ([observation], []))
    monkeypatch.setattr(service, 'match_item', lambda _: [])
    result = service.assess({'stock_count': 1, 'timing': {}})
    assert result['state'] == 'partial'
    assert result['issues'] == ['Larzuk Amulet item 3372686176: unresolved stats 999:12 raw=34']


# --- automatic watcher ----------------------------------------------------------------------------


def key(vendor='Drognan', stat=5):
    cell = {'page': 0, 'x': 0, 'y': 5}
    return {'vendor': vendor, 'txt_id': 351, 'quality': 4, 'identified': True, 'stats': [[0, 7, stat]], **cell}


def scan_result(sentinel, hits=()):
    return {
        'state': 'complete',
        'count': 10,
        'stock_count': 10,
        'hits': list(hits),
        'issues': [],
        'vendors': [sentinel['vendor']] if sentinel else [],
        'timing': {},
        'sentinel': sentinel,
    }


@pytest.fixture
def watcher(tmp_path):
    """A ShopWorker whose probe/capture are scripted; `state['probe']` is what the game shows."""
    displays = []
    state = {'probe': {'state': 'unloaded', 'stock_count': 0}, 'scans': 0, 'appraisal': False, 'clock': 100.0}
    source = SimpleNamespace(pid=7, images={}, capture={}, ensure_connected=lambda: None)

    def capture(*args):
        state['scans'] += 1
        return {'sentinel': state['probe'].get('key')}

    with ThreadPoolExecutor(max_workers=1) as executor:
        check = ShopWorker(
            source,
            executor,
            capture_lock=threading.Lock(),
            focused=lambda _: True,
            display=displays.append,
            output=tmp_path,
            clock=lambda: state['clock'],
            capture=capture,
            evaluate=lambda record: scan_result(record['sentinel'], hits=state.get('hits', ())),
            probe=lambda *args: dict(state['probe']),
            poll_interval=1,
            appraisal_active=lambda: state['appraisal'],
        )
        yield check, displays, state


def settle(check, now=None):
    """Run one poll (if due) and whatever scan it hands over to."""
    started = check.poll(now if now is not None else check.clock())
    if check.future is not None:
        check.future.result(timeout=2)
    return started


def test_watcher_scans_new_stock_once_and_rescans_only_when_first_gear_item_changes(watcher):
    check, displays, state = watcher
    assert settle(check, 100)
    assert state['scans'] == 0  # unloaded: nothing to check, no OSD
    check.tick()
    assert not displays

    state['probe'] = {'state': 'loaded', 'key': key(), 'stock_count': 10, 'vendors': ['Drognan']}
    assert not settle(check, 100.5)  # not due yet
    assert settle(check, 101)
    assert state['scans'] == 1
    check.tick()
    assert 'No shopping targets' in displays[-1][0].text

    for now in (102, 103, 104):  # same stock, no rescan
        assert settle(check, now)
    assert state['scans'] == 1
    state['clock'] = 106  # a no-target result is gone after 5 s even though the shop is still open
    check.tick()
    assert check.visible is None

    state['probe']['key'] = key(stat=6)  # town round trip refreshed the stock
    assert settle(check, 131)
    assert state['scans'] == 2


def test_result_with_targets_stays_ten_seconds_and_reopening_trade_does_not_show_it_again(watcher):
    check, displays, state = watcher
    state['probe'] = {'state': 'loaded', 'key': key(), 'stock_count': 10, 'vendors': ['Drognan']}
    state['hits'] = [
        {'name': 'Kriss', 'vendor': 'Drognan', 'page': 1, 'position': [2, 3], 'reasons': ['+3 Hex: Purge']}
    ]
    settle(check, 100)
    check.tick()
    assert 'Kriss' in displays[-1][1].text
    state['clock'] = 109.9
    settle(check, 109)
    check.tick()
    assert 'Kriss' in displays[-1][1].text
    state['clock'] = 110
    check.tick()
    assert check.visible is None

    state['probe'] = {'state': 'unloaded', 'stock_count': 0}  # Trade closed
    settle(check, 111)
    state['probe'] = {'state': 'loaded', 'key': key(), 'stock_count': 10, 'vendors': ['Drognan']}
    settle(check, 112)
    check.tick()
    assert state['scans'] == 1  # same first gear item: no recheck...
    assert check.visible is None  # ...and no second showing


def test_closing_trade_hides_a_fresh_result_early(watcher):
    check, _displays, state = watcher
    state['probe'] = {'state': 'loaded', 'key': key(), 'stock_count': 10, 'vendors': ['Drognan']}
    state['hits'] = [{'name': 'Kriss', 'vendor': 'Drognan', 'page': 1, 'position': [2, 3], 'reasons': ['x']}]
    settle(check, 100)
    assert check.visible is not None
    state['probe'] = {'state': 'unloaded', 'stock_count': 0}
    settle(check, 101)
    assert check.visible is None


@pytest.mark.parametrize('state_name', ['away', 'no_gear', 'gamble'])
def test_watcher_never_scans_outside_town_or_for_consumable_and_gamble_stock(watcher, state_name):
    check, displays, state = watcher
    state['probe'] = {'state': state_name, 'stock_count': 5, 'key': key() if state_name == 'gamble' else None}
    settle(check, 100)
    assert state['scans'] == 0
    check.tick()
    assert not displays
    if state_name == 'away':
        assert not settle(check, 103)  # backed off outside town
        assert settle(check, 105)


def test_manual_request_always_scans_even_when_stock_is_unchanged(watcher):
    check, displays, state = watcher
    state['probe'] = {'state': 'loaded', 'key': key(), 'stock_count': 10, 'vendors': ['Drognan']}
    settle(check, 100)
    assert state['scans'] == 1
    assert check.request(105, 105)
    check.future.result(timeout=2)
    assert state['scans'] == 2
    check.tick()
    assert 'No shopping targets' in displays[-1][0].text
    assert check.stock_bound


def test_manual_request_during_a_poll_runs_as_a_manual_scan(watcher):
    check, _displays, state = watcher
    started, release = threading.Event(), threading.Event()

    def slow_probe(*args):
        started.set()
        assert release.wait(2)
        return {'state': 'unloaded', 'stock_count': 0}

    check.probe = slow_probe
    assert check.poll(100)
    assert started.wait(2)
    assert check.request(100.5, 100.5)  # accepted, not dropped
    release.set()
    check.future.result(timeout=2)
    assert state['scans'] == 1
    assert json.loads((check.output / 'shop-latest.json').read_text())['manual'] is True
    assert not check.busy


def test_watcher_defers_to_an_active_appraisal(watcher):
    check, _displays, state = watcher
    state['probe'] = {'state': 'loaded', 'key': key(), 'stock_count': 10, 'vendors': ['Drognan']}
    state['appraisal'] = True
    settle(check, 100)
    assert state['scans'] == 0
    state['appraisal'] = False
    settle(check, 101)
    assert state['scans'] == 1
    check.dismiss()  # Alt+D on a vendor item takes the OSD
    state['appraisal'] = True
    settle(check, 102)
    state['appraisal'] = False
    settle(check, 103)
    assert check.visible is None  # a shown result is never brought back
    assert state['scans'] == 1


def test_failed_automatic_scans_stay_quiet_and_stop_retrying_until_stock_changes_or_win_d(watcher):
    check, displays, state = watcher
    state['probe'] = {'state': 'loaded', 'key': key(), 'stock_count': 10, 'vendors': ['Drognan']}
    attempts = {'n': 0}

    def failing(*args):
        attempts['n'] += 1
        raise ValueError('stock changed during scan')

    check.capture = failing
    for now in range(100, 110):
        settle(check, now)
    assert attempts['n'] == 3
    check.tick()
    assert not displays  # the watcher never shows failures

    assert check.request(110, 110)  # Win+D reports and re-arms
    check.future.result(timeout=2)
    assert attempts['n'] == 4
    check.tick()
    assert displays[-1][0].text == 'Shop check unavailable'
    settle(check, 111)
    assert attempts['n'] == 5  # retries re-armed by the manual press


def test_auto_disabled_keeps_the_manual_lease(watcher):
    check, _displays, state = watcher
    check.auto = False
    state['probe'] = {'state': 'loaded', 'key': key(), 'stock_count': 10, 'vendors': ['Drognan']}
    assert not settle(check, 100)
    assert check.request(100, 100)
    check.future.result(timeout=2)
    state['clock'] = 105
    check.tick()
    assert check.visible is None


def test_triage_shop_only_shows_sell_slow_and_self(monkeypatch):
    from inventory_tracking.shop import service
    from inventory_tracking.presentation import Tone

    observations = [
        {'item': {'name': name}, 'vendor': 'Anya', 'source': {'position': [0, 0], 'container': {'page': 0}}}
        for name in ('sell', 'slow', 'self', 'vendor')
    ]
    monkeypatch.setattr(service, 'decode_stock', lambda _: (observations, []))
    monkeypatch.setattr(service, 'match_item', lambda _: pytest.fail('Old shop rules called'))
    result = service.assess(
        {'stock_count': 4, 'timing': {}},
        retrieve=lambda o: {'triage': {'verdict': o['item']['name'], 'reason': 'test', 'band': None}},
    )
    assert [h['name'] for h in result['hits']] == ['sell', 'slow', 'self']
    tones = {line.tone for line in service.result_lines(result)}
    assert {Tone.TIER_HIGH, Tone.TIER_MED, Tone.TIER_LOW} <= tones
