"""The d2-rca skill's `session.py inputs`: a change of a frame's pointer, buttons or keys that no `sent` event
(nor a press in the healer's own log) explains is the player's. The take is written by the recorder itself."""

import argparse
import importlib.util
import json
from datetime import datetime
from pathlib import Path

from inventory_tracking.takes.record import Recorder, Sample
from tests.inventory_tracking.takes.test_record import RECT, Script, world


TOOL = Path(__file__).parents[3] / '.agents/skills/d2-rca/tools/session.py'
spec = importlib.util.spec_from_file_location('rca_session', TOOL)
assert spec is not None
assert spec.loader is not None
session = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session)

LEFT = 1 << 8  # button 1 in XQueryPointer's mask


def frame(x, y, mask=0, keys=()):
    return Sample(world(), [], (x, y, mask), RECT, frozenset(keys))


def recorded(tmp_path):
    """Frames 40 ms apart. The macro moves the pointer and clicks; then the player moves it on, clicks by hand,
    the healer presses belt key 1 (code 10) and the player presses `a` (38)."""
    now = [1.0]
    script = Script(
        frame(100, 100),  # 1.00
        frame(500, 400),  # 1.04: the macro's move (sent at 1.02)
        frame(500, 400, LEFT),  # 1.08: the macro's click (sent 1.06)
        frame(500, 400),  # 1.12: its release (sent 1.10)
        frame(500, 400),  # 1.16
        frame(500, 400),  # 1.20
        frame(500, 400),  # 1.24
        frame(520, 410),  # 1.28: the player's hand (no move of the macro's within 0.15 s)
        frame(520, 410, LEFT),  # 1.32: the player's click
        frame(520, 410),  # 1.36
        frame(520, 410, 0, {10}),  # 1.40: the healer's key
        frame(520, 410),  # 1.44
        frame(520, 410, 0, {38}),  # 1.48: the player's key
        frame(520, 410),  # 1.52
    )
    rec = Recorder(script, output=tmp_path / 'combat', clock=lambda: now[0], manifest=lambda: {'keys': {'10': '1'}})
    sends = {1.02: ('move', (500, 400)), 1.06: ('button', (1, 1)), 1.10: ('button', (1, 0))}
    for step in range(14):
        t = round(1.0 + 0.04 * step, 2)
        if (at := round(t - 0.02, 2)) in sends:
            now[0] = at
            rec.sent(*sends[at])
        now[0] = t
        rec.step(t)
    rec.close('test')
    take = next((tmp_path / 'combat').iterdir())
    clock = json.loads((take / 'manifest.json').read_text())['clock']
    pressed = datetime.fromtimestamp(clock['wall'] + 1.41 - clock['monotonic'])
    log = tmp_path / 'osd' / '20000101T000000Z-x' / 'osd.log'
    log.parent.mkdir(parents=True)
    stamp = pressed.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
    log.write_text(f'{stamp} INFO player healing potion: column 1; item 7; input keyboard\n')
    return take, log


def test_the_players_click_and_key_are_told_from_the_macros_and_the_healers(tmp_path):
    take, log = recorded(tmp_path)
    frames = session.jsonl(take, 'frames.jsonl')
    sent = [e for e in session.jsonl(take, 'events.jsonl') if e['event'] == 'sent']
    clock = session.Clock(json.loads((take / 'manifest.json').read_text()), frames[0]['t'])
    osd = session.osd_presses(log, clock, {'1': 10})
    times, osd_times = [e['t'] for e in sent], [p[0] for p in osd]
    told = [
        (round(c[0], 2), c[1], c[2], session.whose(c, sent, times, osd, osd_times)) for c in session.changes(frames)
    ]
    assert told == [
        (1.04, 'move', (500, 400), 'macro'),
        (1.08, 'button', (1, True), 'macro'),
        (1.12, 'button', (1, False), 'macro'),
        (1.28, 'move', (520, 410), 'player'),
        (1.32, 'button', (1, True), 'player'),
        (1.36, 'button', (1, False), 'player'),
        (1.4, 'key', (10, True), 'healer'),
        (1.44, 'key', (10, False), 'healer'),
        (1.48, 'key', (38, True), 'player'),
        (1.52, 'key', (38, False), 'player'),
    ]


def test_the_command_lists_only_the_players_inputs_and_finds_the_healers_log(tmp_path, capsys):
    take, _ = recorded(tmp_path)
    session.inputs(argparse.Namespace(take=str(take), osd=None, all=False))
    out = capsys.readouterr().out
    assert '1 healer presses' in out
    assert 'button macro 2, button player 2, key healer 2, key player 2, move macro 1, move player 1' in out
    listed = out.split("## the player's inputs")[1].strip().splitlines()
    assert len(listed) == 5  # the stroke, the click's down and up, the key's down and up
    assert 'pointer  1 frames' in listed[0]
    assert 'button 1 down at (520, 410)' in listed[1]
    assert all('[player]' in line for line in listed[1:])


def test_a_pointer_away_from_every_target_the_macro_sent_then_is_the_players_hand_on_it():
    sent = [{'t': 1.0, 'input': 'move', 'xy': [500, 400]}]
    change = (1.04, 'move', (560, 400), {})
    assert session.whose(change, sent, [1.0], [], []) == 'player (during a macro move)'
    assert session.whose((1.04, 'move', (502, 401), {}), sent, [1.0], [], []) == 'macro'
