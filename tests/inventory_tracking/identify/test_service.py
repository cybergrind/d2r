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
        'town': True,
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


def test_full_identify_observation_survives_lookup_failure(parts):
    worker, _state, _displays, _notifications, output = parts

    def fail(observation):
        files = list((output / 'identified').glob('*.json'))
        assert len(files) == 1
        assert json.loads(files[0].read_text())['observation'] == observation
        raise RuntimeError('lookup failed')

    worker.retrieve = fail
    worker._assess(['1'])
    [path] = (output / 'identified').glob('*.json')
    assert json.loads(path.read_text())['observation'] == observation(unit_id=1)
    assert any('lookup failed' in issue for issue in worker.last_result['issues'])


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


def test_an_item_that_arrives_identified_while_gambling_is_assessed(parts):
    # A gambled item never sits unidentified in the inventory: it is new and identified at once.
    worker, state, displays, _, tmp_path = parts
    gambling = {'on': False}
    worker.gambling = lambda: gambling['on']
    state['probe'] = probe_result(a=True) | {'owned': ['1', '3']}  # '3' lies in the stash
    assert worker.poll(100.0)
    wait(worker)
    state['probe'] = probe_result(a=True, b=True) | {'owned': ['1', '2', '3']}
    assert worker.poll(101.0)
    wait(worker)
    assert worker.visible is None  # not gambling: bought, picked up or moved, as before

    gambling['on'] = True
    state['probe'] = probe_result(a=True, b=True, c=True) | {'owned': ['1', '2', '3']}
    assert worker.poll(102.0)
    wait(worker)
    assert worker.visible is None  # taken out of the stash while the gamble stock is still loaded

    state['probe'] = probe_result(a=True, b=True, c=True) | {'owned': ['1', '2', '3', '9']}
    state['probe']['items']['9'] = {'identified': True, 'quality': 6, 'txt_id': 351}
    assert worker.poll(103.0)
    wait(worker)
    worker.tick()
    assert displays[-1][0].text == 'Identified 1 — 1 keep · 0 check · 0 vendor'
    assert json.loads((tmp_path / 'identify-latest.json').read_text())['unit_ids'] == ['9']

    state['probe']['items'].pop('9')  # on the cursor ...
    assert worker.poll(104.0)
    wait(worker)
    state['probe']['items']['9'] = {'identified': True, 'quality': 6, 'txt_id': 351}  # ... and put back
    worker.dismiss()
    assert worker.poll(105.0)
    wait(worker)
    assert worker.visible is None  # assessed once


def test_gambled_items_need_a_baseline_from_before_the_purchase(parts):
    worker, state, _, _, _ = parts
    worker.gambling = lambda: True
    state['probe'] = probe_result(a=True) | {'owned': ['1']}
    assert worker.poll(100.0)
    wait(worker)
    assert worker.visible is None


def test_a_new_pass_adds_to_the_summary_still_on_screen(parts):
    # Gambling one item after another: each result used to replace the previous one at once.
    worker, _state, displays, _, tmp_path = parts
    now = {'t': 100.0}
    worker.clock = lambda: now['t']
    seen = []
    capture = worker.capture

    def watching(pid, images, source, unit_ids):
        seen.append([line.text for line in worker.visible])  # what is shown while the pass runs
        return capture(pid, images, source, unit_ids)

    worker.capture = watching
    worker.decode = lambda record: ([observation(name=f'Ring {u}', unit_id=int(u)) for u in record['unit_ids']], [])
    worker._assess(['1'])
    now['t'] = 105.0
    worker._assess(['2'])

    assert seen[0] == ['Assessing 1 identified items…']
    assert seen[1][0] == 'Identified 1 — 1 keep · 0 check · 0 vendor'  # the first result stays up
    assert seen[1][-1] == 'Assessing 1 identified items…'
    worker.tick()
    texts = [line.text for line in displays[-1]]
    assert texts[0] == 'Identified 2 — 2 keep · 0 check · 0 vendor'
    assert [t.split(':')[0] for t in texts[1::2]] == ['KEEP   Ring 2 (Ring)', 'KEEP   Ring 1 (Ring)']  # newest first
    assert worker.expires == 105.0 + worker.hit_seconds  # the whole card gets a fresh lease
    assert json.loads((tmp_path / 'identify-latest.json').read_text())['unit_ids'] == ['2']  # the file: one pass

    now['t'] = 200.0  # long after the card expired
    worker.tick()
    worker._assess(['3'])
    worker.tick()
    assert displays[-1][0].text == 'Identified 1 — 1 keep · 0 check · 0 vendor'

    worker._assess(['1'])
    worker.dismiss()  # Alt+D takes the screen: the next card starts empty
    worker._assess(['2'])
    worker.tick()
    assert displays[-1][0].text == 'Identified 1 — 1 keep · 0 check · 0 vendor'


def field(probe):
    return probe | {'location': 46, 'town': False}


def test_a_scroll_used_in_the_field_is_assessed(parts):
    worker, state, _, _, tmp_path = parts
    state['probe'] = field(probe_result(a=False, c=True))
    assert worker.poll(100.0)
    wait(worker)
    assert worker.next_poll_delay == pytest.approx(1.0)  # an unidentified item is carried: a scroll may follow
    state['probe'] = field(probe_result(a=True, c=True))
    assert worker.poll(101.0)
    wait(worker)
    assert json.loads((tmp_path / 'identify-latest.json').read_text())['unit_ids'] == ['1']
    assert worker.next_poll_delay == pytest.approx(5.0)  # nothing left to identify out here


def test_an_item_picked_up_and_identified_between_two_field_reads_is_assessed(parts):
    # Nothing unidentified is carried, so the field is read every five seconds: the pickup and the
    # scroll both fit in between, and the item is first seen identified.
    worker, state, _, _, tmp_path = parts
    state['probe'] = field(probe_result(a=True)) | {'owned': ['1', '3']}
    assert worker.poll(100.0)
    wait(worker)
    state['probe'] = field(probe_result(a=True, b=True, c=True)) | {'owned': ['1', '2', '3']}
    assert worker.poll(105.0)
    wait(worker)
    assert json.loads((tmp_path / 'identify-latest.json').read_text())['unit_ids'] == ['2']  # '3' was held before


def test_the_baseline_survives_the_portal_and_a_failed_probe(parts):
    # Cain right after the portal: the last read before him was in the field, or failed.
    worker, state, _, _, tmp_path = parts
    state['probe'] = field(probe_result(a=False, b=False))
    assert worker.poll(100.0)
    wait(worker)
    probe = worker.probe
    worker.probe = lambda *args: (_ for _ in ()).throw(ValueError('Incomplete or unstable inventory snapshot'))
    assert worker.poll(101.0)
    wait(worker)
    assert worker.unidentified == {'1', '2'}
    worker.probe = probe
    state['probe'] = probe_result(a=True, b=True)
    assert worker.poll(102.0)
    wait(worker)
    assert json.loads((tmp_path / 'identify-latest.json').read_text())['unit_ids'] == ['1', '2']


def test_a_new_game_starts_from_a_new_baseline(parts):
    # Unit ids are dealt again in every game; the player's own id tells the games apart.
    worker, state, _, notifications, tmp_path = parts
    state['probe'] = field(probe_result(a=False)) | {'owned': ['1']}
    assert worker.poll(100.0)
    wait(worker)
    state['probe'] = field(probe_result(a=True, b=True)) | {'player_id': 2, 'owned': ['1', '2']}
    assert worker.poll(101.0)
    wait(worker)
    assert notifications == []
    assert not (tmp_path / 'identify-latest.json').exists()
    assert worker.unidentified == set()


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


@pytest.mark.parametrize('base', ['Small Charm', 'Large Charm', 'Grand Charm', 'Jewel', 'Colossal Jewel'])
def test_useful_multiple_copy_items_remain_keep_with_better_owned_copy(base):
    result = saved_result()['result']
    result['extraction']['item'].update(base_name=base, name=base, rarity='magic')
    result.setdefault('assessment', {})['roles'] = [role('matched')]
    owned = {'kind': base, 'count': 3, 'relation': 'worse', 'perfection': None, 'copies': []}
    assert verdict_for(result, owned)[0] == 'keep'


@pytest.mark.parametrize('status', ['candidate', 'premium'])
def test_qualified_trade_item_is_keep_even_when_a_better_copy_satisfies_build(status):
    result = saved_result()['result']
    result.setdefault('assessment', {}).update(
        roles=[role('matched')], trade_qualification={'status': status, 'reason': 'Reviewed valuable combination.'}
    )
    owned = {'kind': 'Ring', 'count': 2, 'relation': 'worse', 'perfection': None, 'copies': []}
    assert verdict_for(result, owned) == ('keep', 'Reviewed valuable combination.')


@pytest.mark.parametrize(('unstable_reads', 'state'), [(2, 'complete'), (3, 'partial')])
def test_snapshot_that_changed_during_the_read_is_read_again(parts, unstable_reads, state):
    worker, probe_state, _, _, tmp_path = parts
    reads = []

    def decode(record):
        reads.append(record)
        if len(reads) <= unstable_reads:
            return [], [f'Item {u}: Unstable item snapshot' for u in record['unit_ids']]
        return [observation(unit_id=int(u)) for u in record['unit_ids']], []

    worker.decode, worker.retry_delay = decode, 0
    assert worker.poll(100.0)
    wait(worker)
    probe_state['probe'] = probe_result(a=True, b=False, c=True)
    assert worker.poll(101.0)
    wait(worker)
    latest = json.loads((tmp_path / 'identify-latest.json').read_text())
    assert len(reads) == 3  # the first read and at most two more
    assert latest['state'] == state


def test_focus_loss_hides_the_card_without_cancelling_the_pass(parts):
    worker, state, displays, _, _ = parts
    started, release = threading.Event(), threading.Event()

    def slow_retrieve(observation):
        started.set()
        assert release.wait(5)
        return valuable(observation)

    worker.retrieve = slow_retrieve
    assert worker.poll(100.0)
    wait(worker)
    state['probe'] = probe_result(a=True, b=False, c=True)
    assert worker.poll(101.0)
    assert started.wait(5)
    worker.focused = lambda _: False  # e.g. one failed focus probe while "Assessing…" shows
    worker.tick()
    assert displays[-1] == []
    release.set()
    wait(worker)
    worker.tick()
    assert displays[-1] == []  # still unfocused: hidden, not dropped
    worker.focused = lambda _: True
    worker.tick()
    assert displays[-1][0].text.startswith('Identified 1 — 1 keep')


def test_lookups_of_one_pass_run_in_parallel_and_keep_item_order(parts):
    worker, state, _, _, tmp_path = parts
    both = threading.Barrier(2)

    def retrieve(observation):
        both.wait(5)  # passes only when the two lookups overlap
        return valuable(observation)

    worker.retrieve = retrieve
    with ThreadPoolExecutor(max_workers=2) as lookups:
        worker.lookup_executor = lookups
        assert worker.poll(100.0)
        wait(worker)
        state['probe'] = probe_result(a=True, b=True, c=True)
        assert worker.poll(101.0)
        wait(worker)
    latest = json.loads((tmp_path / 'identify-latest.json').read_text())
    assert latest['state'] == 'complete'
    assert [item['unit_id'] for item in latest['items']] == [1, 2]


def test_triage_overrides_build_keep_and_uses_sell_colors():
    result = saved_result()['result']
    result['triage'] = {'verdict': 'slow', 'reason': 'asks 0.25 Ist median', 'band': None}
    summary = item_summary(observation(), result)
    assert summary['verdict'] == 'slow'
    lines = result_lines({'state': 'complete', 'items': [summary], 'issues': []})
    assert any('1 slow' in line.text for line in lines)
    assert any(line.tone == Tone.TIER_MED for line in lines)
    result['triage']['verdict'] = 'vendor'
    assert verdict_for(result)[0] == 'vendor'


def test_slow_items_are_one_count_line_and_do_not_push_out_priority_items():
    slow = {
        'verdict': 'slow',
        'triage': {'decision_ist': 0.3},
        'name': 'Slow item',
        'stats': [],
        'tone': 'unique',
        'reason': 'asks',
    }
    items = [slow.copy() for _ in range(7)]
    items[-1] = slow | {'triage': {'decision_ist': 0.8}}
    items.append(slow | {'verdict': 'self', 'name': 'Own charm'})
    result = {'state': 'complete', 'items': items, 'issues': []}
    text = '\n'.join(line.text for line in result_lines(result))
    assert '7 slow, cheapest asks 0.3-0.8 Ist' in text
    assert 'Own charm' in text
    assert 'Slow item' not in text
    assert len(result['items']) == 8


@pytest.mark.parametrize('trade_verdict', ['vendor', 'slow', 'sell', 'check'])
def test_identify_keeps_high_leveling_use_visible_alongside_trade(trade_verdict):
    result = {
        'triage': {'verdict': trade_verdict, 'reason': 'below keep price', 'band': None},
        'assessment': {'leveling': [{'tier': 'high', 'required_level': 33, 'reason': 'Explosive arrows with pierce.'}]},
    }
    summary = item_summary(observation('Kuko Shakaku', rarity='unique'), result)
    assert summary['verdict'] == ('check' if trade_verdict in ('vendor', 'slow') else trade_verdict)
    lines = result_lines({'state': 'complete', 'items': [summary], 'issues': []})
    assert any('leveling high (level 33)' in line.text for line in lines)
    assert 'Explosive arrows with pierce' in summary['reason']
    assert result['triage']['verdict'] == trade_verdict


@pytest.mark.parametrize(
    'use',
    [
        {'tier': 'med', 'reason': 'Ordinary progression.'},
        {'tier': 'high', 'generic': True, 'reason': 'Generic progression.'},
    ],
)
def test_triage_does_not_alert_for_generic_or_mid_leveling(use):
    result = {'triage': {'verdict': 'vendor', 'reason': 'below keep price'}, 'assessment': {'leveling': [use]}}
    assert verdict_for(result) == ('vendor', 'below keep price')
