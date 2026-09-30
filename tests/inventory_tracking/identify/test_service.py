"""Identify watcher: baseline, newly identified items, assessment lines and quiet failures."""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from inventory_tracking.appraisal.owned import RELATION_TEXT
from inventory_tracking.identify.service import (
    IdentifyWorker,
    compact_stat,
    describe,
    item_summary,
    result_lines,
    verdict_for,
)
from inventory_tracking.presentation import Tone
from tests.inventory_tracking.appraisal.test_text import saved_result


def probe_result(**items):
    """Unit ids are decimal strings in probes (`a` → '1', `b` → '2', `c` → '3')."""
    ids = {'a': '1', 'b': '2', 'c': '3'}
    return {
        'state': 'ok',
        'location': 1,
        'player_id': 1,
        'items': {ids[k]: {'identified': v, 'quality': 4, 'txt_id': 351} for k, v in items.items()},
    }


def observation(name='Ring', unit_id=7, rarity='magic'):
    return {
        'item': {'name': name, 'base_name': 'Ring', 'rarity': rarity},
        'source': {'unit_id': unit_id},
        'decoded_stats': [
            {
                'status': 'decoded',
                'name': 'fireresist',
                'value': 11,
                'text': 'Fire Resist +11% (3-15%) [T2]',
                'roll_tier': 2,
            },
            {
                'status': 'decoded',
                'name': 'item_fastercastrate',
                'value': 10,
                'text': '+10% (10-10%) Faster Cast Rate [T1]',
                'roll_tier': 1,
            },
            {
                'status': 'decoded',
                'name': 'lightmindam',
                'value': 1,
                'text': '+1 (1-1) to Minimum Lightning Damage [T1]',
                'roll_tier': 1,
            },
            {
                'status': 'decoded',
                'name': 'lightmaxdam',
                'value': 14,
                'text': '+14 (11-23) to Maximum Lightning Damage [T1]',
                'roll_tier': 1,
            },
            {
                'status': 'decoded',
                'name': 'item_addclassskills',
                'value': 2,
                'text': '+2 to Amazon Skill Levels',
                'roll_tier': 3,
            },
            {'status': 'unresolved', 'text': 'unknown stat 999'},
        ],
    }


def valuable(observation):
    result = saved_result()['result']
    result['value_watch'] = [
        {'details': {'priority': 'valuable_candidate', 'build_contexts': [], 'roll_bucket': 'top roll'}}
    ]
    result['price_estimate'] = {'estimate_ist': 2.5, 'confidence': 'medium', 'dates': ['2026-09-18']}
    return result


@pytest.fixture
def parts(tmp_path):
    displays, notifications = [], []
    state = {'probe': probe_result(a=False, b=False, c=True), 'appraisal': False}
    source = SimpleNamespace(pid=7, images={}, capture={}, ensure_connected=lambda: None)
    with ThreadPoolExecutor(max_workers=1) as executor:
        worker = IdentifyWorker(
            source,
            executor,
            capture_lock=threading.Lock(),
            focused=lambda _: True,
            display=displays.append,
            output=tmp_path,
            retrieve=valuable,
            notify=lambda title, body: notifications.append((title, body)),
            clock=lambda: 100.0,
            probe=lambda *args: state['probe'],
            capture=lambda pid, images, capture, unit_ids: {'unit_ids': list(unit_ids)},
            decode=lambda record: ([observation(unit_id=int(u)) for u in record['unit_ids']], []),
            appraisal_active=lambda: state['appraisal'],
        )
        yield worker, state, displays, notifications, tmp_path


def wait(worker):
    worker.future.result(timeout=5)


def test_first_read_is_a_baseline_and_newly_identified_items_are_assessed(parts):
    worker, state, displays, notifications, tmp_path = parts
    assert worker.poll(100.0)
    wait(worker)
    assert worker.unidentified == {'1', '2'}
    assert worker.visible is None
    state['probe'] = probe_result(a=True, b=False, c=True)
    assert worker.poll(101.0)
    wait(worker)
    assert worker.unidentified == {'2'}
    worker.tick()
    lines = displays[-1]
    assert lines[0].text == 'Identified 1 — 1 keep · 0 check · 0 vendor'
    assert lines[0].tone == Tone.VALUABLE
    assert lines[1].text == 'KEEP   Ring: +10 FCR · FR +11% · +2 Amazon skills'
    assert lines[1].tone == Tone.MAGIC
    assert lines[2].text == '       valuable: top roll'
    assert lines[2].tone == Tone.VALUABLE
    assert notifications == [('Identified 1: 1 keep · 0 check · 0 vendor', 'KEEP Ring — valuable: top roll')]
    latest = json.loads((tmp_path / 'identify-latest.json').read_text())
    assert latest['unit_ids'] == ['1']
    assert latest['state'] == 'complete'
    assert latest['items'][0]['verdict'] == 'keep'


def test_unchanged_inventory_and_items_that_left_do_nothing(parts):
    worker, state, _, notifications, _ = parts
    assert worker.poll(100.0)
    wait(worker)
    assert worker.poll(101.0)
    wait(worker)
    state['probe'] = probe_result(b=False, c=True)  # 'a' was sold or moved, not identified
    assert worker.poll(102.0)
    wait(worker)
    assert worker.unidentified == {'2'}
    assert notifications == []
    assert worker.visible is None


def test_leaving_town_or_a_failed_probe_forgets_the_baseline(parts):
    worker, state, _, notifications, _ = parts
    assert worker.poll(100.0)
    wait(worker)
    state['probe'] = {'state': 'away', 'location': 46, 'player_id': 1, 'items': {}}
    assert worker.poll(101.0)
    wait(worker)
    assert worker.unidentified is None
    assert worker.next_poll_delay == pytest.approx(5.0)
    state['probe'] = probe_result(a=True, b=True)  # identified while away: nothing to announce
    assert worker.poll(110.0)
    wait(worker)
    assert notifications == []


def test_polls_wait_for_the_interval_and_for_alt_d(parts):
    worker, state, _, _, _ = parts
    state['appraisal'] = True
    assert worker.poll(100.0)
    wait(worker)
    assert worker.unidentified is None  # skipped: Alt+D owns the reader and the OSD
    assert not worker.poll(100.5)
    state['appraisal'] = False
    assert worker.poll(101.0)
    wait(worker)
    assert worker.unidentified == {'1', '2'}


def test_progress_line_blinks_for_one_second_only(parts):
    worker, state, displays, _, _ = parts
    started, release = threading.Event(), threading.Event()

    def slow_capture(pid, images, capture, unit_ids):
        started.set()
        assert release.wait(5)
        return {'unit_ids': list(unit_ids)}

    worker.capture = slow_capture
    assert worker.poll(100.0)
    wait(worker)
    state['probe'] = probe_result(a=True, b=False, c=True)
    assert worker.poll(101.0)
    assert started.wait(5)
    worker.tick()
    assert displays[-1][0].text == 'Assessing 1 identified items…'
    worker.clock = lambda: 101.0  # one second after the 100.0 start: already gone
    worker.tick()
    assert displays[-1] == []
    release.set()
    wait(worker)
    worker.clock = lambda: 100.0
    worker.tick()
    assert displays[-1][0].text.startswith('Identified 1 —')


def test_retrieval_failures_become_issues_not_crashes(parts):
    worker, state, displays, notifications, tmp_path = parts

    def fail(observation):
        raise ValueError('index changed')

    worker.retrieve = fail
    assert worker.poll(100.0)
    wait(worker)
    state['probe'] = probe_result(a=True, b=True, c=True)
    assert worker.poll(101.0)
    wait(worker)
    worker.tick()
    assert displays[-1][0].text == 'Identified 0 — 0 keep · 0 check · 0 vendor'
    assert displays[-1][-1].text == '2 read/decode issues; result is incomplete'
    assert json.loads((tmp_path / 'identify-diagnostics.json').read_text())['result']['state'] == 'partial'
    assert notifications == []  # nothing particular: no desktop notification


def role(status, build='fire-blast-assassin', name='Starter cold-resistance ring'):
    return {
        'id': f'{build}-{status}',
        'build': build,
        'side': 'player',
        'slot': 'Ring',
        'role': name,
        'status': status,
        'matched': ['Required item properties are satisfied.'] if status != 'failed' else [],
        'missing': ['Verify loadout.'] if status == 'partial' else [],
    }


@pytest.mark.parametrize(
    ('patch', 'expected'),
    [
        ({}, ('vendor', 'no build rules for this item; no supported estimate')),
        (
            {'assessment': {'roles': [role('failed'), role('failed')]}},
            ('vendor', 'no build use (2 rules failed); no supported estimate'),
        ),
        (
            {'assessment': {'roles': [role('failed'), role('partial'), role('partial', 'nova-sorceress-guide')]}},
            (
                'check',
                'possible: Fire Blast Assassin player Starter cold-resistance ring +1; needs review: Verify loadout.',
            ),
        ),
        (
            {'assessment': {'leveling': [{'tier': 'med', 'reason': 'Cast rate when needed; otherwise life. More.'}]}},
            ('check', 'leveling mid: Cast rate when needed; otherwise life'),
        ),
        (
            {'assessment': {'leveling': [{'tier': 'med', 'generic': True, 'reason': 'Cast rate when needed.'}]}},
            ('vendor', 'no build rules for this item; no supported estimate'),
        ),
        ({'assessment': {'trade_tier': {'status': 'reviewed', 'tier': 'low'}}}, ('check', 'trade tier low')),
        ({'assessment': {'trade_tier': {'status': 'reviewed', 'tier': 'med'}}}, ('keep', 'trade tier mid')),
        (
            {'assessment': {'roles': [role('matched')]}},
            ('keep', 'build use: Fire Blast Assassin player Starter cold-resistance ring'),
        ),
        ({'price_estimate': {'estimate_ist': 0.4}}, ('check', 'asks ~0.4 Ist')),
        ({'price_estimate': {'estimate_ist': 3}}, ('keep', 'asks ~3 Ist')),
        (
            {'value_watch': [{'details': {'priority': 'build_demand', 'stat_priority': '10 FCR + resists'}}]},
            ('keep', 'build demand: 10 FCR + resists'),
        ),
    ],
)
def test_verdicts_follow_the_assessment_evidence(patch, expected):
    result = saved_result()['result']
    for key, value in patch.items():
        if isinstance(value, dict):
            result.setdefault(key, {}).update(value)
        else:
            result[key] = value
    assert verdict_for(result) == expected


def test_cube_items_are_tagged():
    cube = observation('Amulet')
    cube['source']['container'] = {'page': 3, 'name': 'Horadric Cube'}
    assert item_summary(cube, saved_result()['result'])['name'] == 'Amulet (Ring) [cube]'


def test_compact_stats_drop_roll_annotations_and_abbreviate():
    assert compact_stat('Fire Resist +14% (5-40%) [T3; T1: 31-40%]') == 'FR +14%'
    assert compact_stat('+10% (10-10%) Faster Cast Rate [T1; T1: 10-10%]') == '+10 FCR'
    assert compact_stat('Adds 1 (1-1) [T1]-14 (11-23) [T1] Lightning Damage') == 'Adds 1-14 Lightning Damage'
    assert compact_stat('+31 to Life') == '+31 life'
    assert compact_stat('Magic Damage Reduced by 3 (1-3) [T1; T1: 3-3]') == 'Magic Damage Reduced by 3'


def test_summary_of_an_unwanted_ring_says_vendor_and_expires_from_the_osd(parts):
    worker, _, displays, _, _ = parts
    summary = item_summary(observation('Ring', rarity='magic'), saved_result()['result'])
    assert summary == {
        'name': 'Ring',
        'rarity': 'magic',
        'tone': 'magic',
        'verdict': 'vendor',
        'reason': 'no build rules for this item; no supported estimate',
        'stats': ['+10 FCR', 'FR +11%', '+2 Amazon skills'],
        'estimate_ist': None,
        'unit_id': 7,
    }
    result = {'state': 'complete', 'items': [summary], 'issues': []}
    # Vendor items are counted, not listed, and raise no notification.
    assert [line.text for line in result_lines(result)] == ['Identified 1 — 0 keep · 0 check · 1 vendor']
    assert result_lines(result)[0].tone == Tone.METADATA
    assert describe(result) is None
    checked = {**summary, 'verdict': 'check', 'reason': 'possible: Fire Blast Assassin player ring'}
    both = {'state': 'complete', 'items': [summary, checked], 'issues': []}
    assert [line.text for line in result_lines(both)] == [
        'Identified 2 — 0 keep · 1 check · 1 vendor',
        'CHECK  Ring: +10 FCR · FR +11% · +2 Amazon skills',
        '       possible: Fire Blast Assassin player ring',
    ]
    assert result_lines(both)[2].tone == Tone.DEMAND
    assert describe(both) == (
        'Identified 2: 0 keep · 1 check · 1 vendor',
        'CHECK Ring — possible: Fire Blast Assassin player ring',
    )
    worker.visible, worker.expires = result_lines(result), 105.0
    worker.tick()
    assert displays[-1][0].text.startswith('Identified')
    worker.clock = lambda: 105.0
    worker.tick()
    assert displays[-1] == []
    assert worker.visible is None


def test_notable_stats_fold_elemental_components_and_equal_resistances():
    from inventory_tracking.identify.service import notable_stats

    rows = [
        {'status': 'decoded', 'name': n, 'value': 11, 'text': f'{n} +11%', 'roll_tier': 2}
        for n in ('fireresist', 'lightresist', 'coldresist', 'poisonresist')
    ]
    rows += [
        {
            'status': 'decoded',
            'name': 'lightmindam',
            'value': 1,
            'text': '+1 to Minimum Lightning Damage',
            'roll_tier': 1,
        },
        {
            'status': 'decoded',
            'name': 'lightmaxdam',
            'value': 14,
            'text': '+14 to Maximum Lightning Damage',
            'roll_tier': 1,
        },
        {'status': 'decoded', 'name': 'coldlength', 'value': 25, 'text': 'Base cold duration'},
        {'status': 'decoded', 'name': 'maxhp', 'value': 31, 'text': '+31 to Life', 'roll_tier': 3},
    ]
    assert notable_stats({'decoded_stats': rows}, limit=5) == ['@ +11%', '+31 life', 'Adds 1-14 Lightning Damage']


def test_alt_d_dismisses_a_showing_summary_at_once(parts):
    from inventory_tracking.appraisal.service import dispatch

    worker, _, displays, _, _ = parts
    summary = item_summary(observation('Ring'), saved_result()['result'])
    worker.visible, worker.expires = result_lines({'state': 'complete', 'items': [summary], 'issues': []}), 200.0
    worker.tick()
    assert displays[-1][0].text.startswith('Identified')
    appraisal = SimpleNamespace(request=lambda t, now: True)
    assert dispatch(b'100.0', 100.2, appraisal, None, None, worker)
    assert worker.visible is None
    assert displays[-1] == []
    worker.tick()
    assert displays[-1] == []  # nothing re-shown after the dismissal
    rejected = SimpleNamespace(request=lambda t, now: False)
    worker.visible = result_lines({'state': 'complete', 'items': [summary], 'issues': []})
    assert not dispatch(b'100.0', 100.2, rejected, None, None, worker)
    assert worker.visible is not None  # a debounced/stale hotkey changes nothing


def test_timing_of_each_phase_is_published_and_logged(parts, caplog):
    worker, state, _, _, tmp_path = parts
    moment = [100.0]

    def clock():  # every look at the clock costs 10 ms, so each phase has a positive duration
        moment[0] += 0.01
        return moment[0]

    worker.clock = clock
    assert worker.poll(100.0)
    wait(worker)
    state['probe'] = probe_result(a=True, b=True, c=True)
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        assert worker.poll(101.0)
        wait(worker)
    latest = json.loads((tmp_path / 'identify-latest.json').read_text())
    timing = latest['timing']
    assert set(timing) >= {
        'items',
        'lock_wait_ms',
        'capture_ms',
        'decode_ms',
        'retrieve_ms',
        'retrieve_max_ms',
        'total_ms',
    }
    assert timing['items'] == 2
    assert [r['name'] for r in timing['retrievals']] == ['Ring', 'Ring']
    assert timing['retrieve_ms'] > 0
    assert timing['retrieve_max_item'] == 'Ring'
    assert timing['total_ms'] == latest['elapsed_ms']
    assert timing['capture_ms'] + timing['decode_ms'] + timing['retrieve_ms'] <= timing['total_ms']
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Identify timing')]
    assert len(lines) == 1
    assert '2 items' in lines[0]
    assert 'retrieve' in lines[0]
    assert any(r.getMessage().startswith('Identify probe:') for r in caplog.records)


@pytest.mark.parametrize(
    ('relation', 'expected'),
    [('worse', 'check'), ('equal', 'check'), ('same', 'check'), ('better', 'keep'), ('mixed', 'keep')],
)
def test_build_use_keep_becomes_check_when_an_owned_copy_rolls_at_least_as_well(relation, expected):
    result = saved_result()['result']
    result.setdefault('assessment', {})['roles'] = [role('matched')]
    owned = {'kind': 'unique Ring', 'count': 1, 'relation': relation, 'perfection': None, 'copies': []}
    assert verdict_for(result, owned)[0] == expected
    summary = item_summary(observation('Amulet'), result, owned)
    assert summary['verdict'] == expected
    assert summary['reason'].endswith('; owned 1: ' + RELATION_TEXT[relation])


def test_trade_reasons_stay_keep_with_an_owned_copy():
    result = saved_result()['result']
    result['price_estimate'] = {'estimate_ist': 3}
    owned = {'kind': 'unique Ring', 'count': 2, 'relation': 'worse', 'perfection': None, 'copies': []}
    assert verdict_for(result, owned) == ('keep', 'asks ~3 Ist')
