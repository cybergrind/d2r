"""The loop-watch tools' log lines as a contract (the d2-loop-watch skill's tools/logwords.py, 2026-10-18).

The tools read serve's prose log; nothing pinned its wording (rca/2026-10-18/arch-observability.md §1). Here:

- every pattern matches a line copied from a real probe.log and yields the groups the tools read;
- the core lines are built from the production code's own format strings (read from the source, so a module being
  edited need not import) or functions (`census`), so a rewording in inventory_tracking fails here, not in a measure;
- the tools hold no line pattern of their own;
- the click rule (`games.clicked`) that watch.py and games.py share: an item a pickup clicked and the census never saw
  again is taken, without a `picked up` line.
"""

import ast
import importlib
import logging
import sys
from pathlib import Path

import pytest

from inventory_tracking.game.decode import census
from inventory_tracking.items.identity import ETHEREAL_FLAG, SOCKETED_FLAG


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / '.agents' / 'skills' / 'd2-loop-watch' / 'tools'
PRODUCTION = ROOT / 'inventory_tracking'
sys.path.insert(0, str(TOOLS))
logwords = importlib.import_module('logwords')
games = importlib.import_module('games')
watch = importlib.import_module('watch')
trade = importlib.import_module('trade')


# --- Real lines (runs/alt-d/*/probe.log), each with the groups the tools read ---------------------------------------

REAL = [
    ('LEG', '2026-10-18 15:58:35,969 INFO Macro: Loop: game 1, what is left', ('1', 'what is left')),
    (
        'FIGHT',
        '2026-10-19 09:27:43,584 INFO Macro: fight (right click): 2 casts seen in 1.4s, 5 down; Yielded (the key asks '
        'for a move)',
        ('1.4',),
    ),
    (
        'TARGET',
        '2026-10-19 09:27:40,514 INFO Macro: agenda: target the elite 279 (1817783950) (kill, tier 4, 2 leaders known '
        'here)',
        ('kill',),
    ),
    (
        'TARGET',
        '2026-10-19 09:20:11,002 INFO Macro: agenda: target Amulet, on the way (pickup, tier 3, 1 leaders known here)',
        ('pickup',),
    ),
    (
        'RESUMED',
        '2026-10-18 15:58:35,613 INFO Macro: resumed after a restart: loop on, pickup sure valuables, run Andariel',
        ('on', 'Andariel'),
    ),
    (
        'STOPPED',
        '2026-10-18 15:53:19,020 INFO Macro: loop stopped: Ring at (22553, 9560) was not picked up after 2 trips back; '
        'Ring lies on the ground: the loop stops here',
        ('Ring at (22553, 9560) was not picked up after 2 trips back; Ring lies on the ground: the loop stops here',),
    ),
    (
        'LEFT',
        '2026-10-18 14:42:14,194 INFO Macro: loop: the waypoint is not under the pointer at any aim: the game is left '
        'and the loop goes on',
        ('the waypoint is not under the pointer at any aim',),
    ),
    (
        'GROUND',
        '2026-10-18 15:58:35,988 INFO Macro: ground: magic Ring at (22562, 9539): taken (material)',
        ('magic', 'Ring', None, None, None, '22562', '9539', 'material'),
    ),
    (
        'GROUND',
        '2026-10-18 15:59:23,732 INFO Macro: ground: magic Assault Helmet "Magic Assault Helmet" at (22557, 9558): '
        'taken (shown)',
        ('magic', 'Assault Helmet', None, None, 'Magic Assault Helmet', '22557', '9558', 'shown'),
    ),
    (
        'GROUND',
        '2026-10-18 15:25:55,457 INFO Macro: ground: superior Broad Axe eth socketed at (22577, 9586): left',
        ('superior', 'Broad Axe', ' eth', ' socketed', None, '22577', '9586', None),
    ),
    (
        'GROUND',  # a base's rolls fold into the name (logwords.py GROUND): the label is read apart
        '2026-10-18 03:09:41,993 INFO Macro: ground: magic Sacred Rondache 0os "Magic Sacred Rondache" at (5172, '
        '3022): taken (shown)',
        ('magic', 'Sacred Rondache 0os', None, None, 'Magic Sacred Rondache', '5172', '3022', 'shown'),
    ),
    (
        'PICKED',
        '2026-10-18 15:58:41,388 INFO Macro: picked up Ring 0.08s after the click (0, -24) pixels from its ground, '
        'from 0.7 away; under the pointer (4, 1235397469)',
        ('Ring',),
    ),
    (
        'PICKED',
        '2026-10-18 15:58:41,402 INFO Macro: picked up Ring 1.18s after the click, late: carried at a later look; at '
        '(22553.0, 9560.0)',
        ('Ring',),
    ),
    (
        'AIMED',
        '2026-10-18 15:58:35,995 INFO Macro: pickup: 3 drops (healing, valuable), belt short (0, 0), life 1751/1751; '
        'Ring at (22553, 9560)',
        ('Ring', '22553', '9560', None, None, None),
    ),
    (
        'AIMED',
        '2026-10-18 15:58:40,661 INFO Macro: aims for Ring (unit 1235397469) at (22553.0, 9560.0), 1 wanted and 2 '
        'other drops: (0, -24) wanted [flag 0x101 type 4 id 1235397469 tail 0x160016] clicked clicked; (0, -54) (4, '
        '3174313323) [flag 0x101 type 4 id 3174313323 tail 0x160016];',
        (None, None, None, 'Ring', '22553.0', '9560.0'),
    ),
    (
        'PICKUP',
        '2026-10-18 15:58:35,995 INFO Macro: pickup: 3 drops (healing, valuable), belt short (0, 0), life 1751/1751; '
        'Ring at (22553, 9560)',
        ('Ring',),
    ),
    (
        'FULL',
        '2026-10-18 11:46:36,925 INFO Macro: stash: the Twisted Essence of Suffering stack is full',
        ('Twisted Essence of Suffering',),
    ),
    (
        'VISIT_STOPS',
        '2026-10-18 16:00:12,913 INFO Macro: trade session done: cube 0 items, block 2x4 free, 9 inventory cells '
        'free, junk left 0, keys 17, portals from the Sling, staff ?, ground clear, 27.6 s (cain 3.5, stash 12.7, '
        'jamella 8.4, halbu -, walk 2.9)',
        ('3.5', '8.4'),
    ),
    ('IDENTIFIED', '2026-10-18 15:59:47,997 INFO Macro: Cain: 7 of 7 items identified', ('7', '7')),
    ('IDENTIFIED', '2026-10-17 11:47:44,494 INFO Macro: identify: 1 of 1 items identified', ('1', '1')),
    (
        'APPRAISED',
        '2026-10-18 15:59:48,821 INFO Macro: identify: appraised magic Large Charm (619) at (3, 0): vendor',
        (None, 'magic', 'Large Charm', '619', 'vendor'),
    ),
    (
        'APPRAISED',
        '2026-10-17 11:23:48,179 INFO Macro: identify: appraised the item 380 at (3, 0): vendor',
        ('380', None, None, None, 'vendor'),
    ),
    (
        'SOLD',
        '2026-10-18 16:00:08,028 INFO Macro: shop: sold the item 658 at (4, 1) for 962 gold: magic Jewel (658)',
        ('658', '962', 'magic Jewel (658)'),
    ),
    ('SOLD', '2026-10-17 11:23:55,380 INFO Macro: shop: sold the item 380 at (3, 0)', ('380', None, None)),
    (
        'UNSOLD',
        '2026-10-18 12:43:02,825 INFO Macro: shop: could not sell the item 669 at (2, 3): white Twisted Essence of '
        'Suffering (669)',
        ('669',),
    ),
    (
        'AFTER',
        '2026-10-18 16:00:09,961 INFO Macro: shop: carried gold 500083 -> 507731 after the sales',
        ('500083', '507731'),
    ),
    (
        'REPAIRED',
        '2026-10-17 21:46:23,212 INFO Macro: repair: the staff 9 -> 69 charges (of 69), gold 254382 -> 152270',
        ('9', '69', '254382', '152270'),
    ),
    ('KILL', '2026-10-18 15:59:24,412 INFO Boss kill: Andariel, 284 this launch', ()),
    (
        'OPENED',
        '2026-10-18 15:58:36,182 INFO Combat take 20261018T125836Z-37 opened in area 37',
        ('20261018T125836Z-37', '37'),
    ),
    ('CREATING', '2026-10-18 15:58:42,386 INFO Macro: Creating cyberr4', ('cyberr4',)),
    (
        'DOOR_MARKED',
        '2026-10-18 15:59:04,365 INFO Macro: door Next level marked at (22592.5, 6517.5); the character at (22591.5, '
        '6522.5), 5.1 from the mark; entry remembered -1.0, +5.0 from the mark',
        ('5.1',),
    ),
    (
        'DOOR_IN',
        '2026-10-18 15:59:04,641 INFO Macro: door Next level: in after 0.28s, walked 0.0 from (22591.5, 6522.5) to '
        '(22591.5, 6522.5); the entry at -1.0, +5.0 from the mark, 5.1 away (remembered)',
        ('0.28', '0.0'),
    ),
    (
        'LEG_TIME',
        '2026-10-18 15:59:04,238 INFO Macro: leg time: level run (at Next level: going through takes a press): 0 '
        'units in 6.6s since its first leg, 0.0 units/s; 0 jumps, 0 walks; key to key none',
        ('0', '6.6', '0', '0'),
    ),
]

# Real lines that a substring names (the tools test `WORD in line`)
WORDS = [
    ('LOOP_ON', '2026-10-18 15:58:35,938 INFO Macro: Loop on'),
    ('LOOP_OFF', '2026-10-18 11:16:57,707 INFO Macro: Loop off'),
    ('LOOP_RESUMED', '2026-10-18 15:58:35,937 INFO Macro: Loop resumed after a restart'),
    ('REQUEST_LOOP', '2026-10-18 11:16:57,355 INFO Macro: request loop, 0 ms old, while loop'),
    (
        'RESUMED_OFF',
        '2026-10-18 13:35:17,831 INFO Macro: resumed after a restart: loop off, pickup sure valuables, run Andariel',
    ),
    ('MACRO_STOPPED', '2026-10-18 15:58:40,662 INFO Macro stopped: Ring was under the pointer at 3 aims and no click '),
    ('TELEPORT', '2026-10-18 15:58:40,742 INFO Macro: Teleport toward Ring: 0 left after this'),
    ('GAME_LOADED', '2026-10-18 15:58:49,111 INFO Macro: game loaded 5.15s after Enter'),
    ('SAVE_AND_EXIT', '2026-10-18 15:58:41,505 INFO Macro: Save and Exit'),
    ('ROUTE_ENTER', '2026-10-18 15:59:04,350 INFO Macro: route Andariel: enter Next level'),
    ('RUN_TO_NEXT', '2026-10-18 15:58:57,453 INFO Macro: Run: to Next level, clearing the way'),
]


@pytest.mark.parametrize(('name', 'line', 'groups'), REAL, ids=[f'{n}-{i}' for i, (n, _, _) in enumerate(REAL)])
def test_a_real_line_yields_its_groups(name: str, line: str, groups: tuple) -> None:
    found = getattr(logwords, name).search(line)
    assert found is not None
    assert found.groups() == groups


@pytest.mark.parametrize(('name', 'line'), WORDS, ids=[n for n, _ in WORDS])
def test_a_real_line_holds_its_word(name: str, line: str) -> None:
    assert getattr(logwords, name) in line


def test_the_stamp_is_the_lines_local_time() -> None:
    line = '2026-10-18 15:58:35,969 INFO Macro: Loop: game 1, what is left'
    assert str(logwords.stamp(line)) == '2026-10-18 15:58:35.969000'
    assert logwords.stamp('Traceback (most recent call last):') is None


# --- Lines built from the production code ----------------------------------------------------------------------------


def literal(node: ast.expr) -> str:
    """A string literal's text."""
    assert isinstance(node, ast.Constant)
    assert isinstance(node.value, str)
    return node.value


def template(node: ast.JoinedStr) -> str:
    """An f-string as a str.format template: its text, '{}' for each value (with its conversion and spec)."""
    parts = []
    for value in node.values:
        if isinstance(value, ast.Constant):
            parts.append(str(value.value).replace('{', '{{').replace('}', '}}'))
        elif isinstance(value, ast.FormattedValue):
            conversion = '' if value.conversion == -1 else f'!{chr(value.conversion)}'
            spec = f':{template(value.format_spec)}' if isinstance(value.format_spec, ast.JoinedStr) else ''
            parts.append(f'{{{conversion}{spec}}}')
    return ''.join(parts)


def produced(path: str, anchor: str) -> list[str]:
    """The strings of `inventory_tracking/<path>` that hold `anchor`, docstrings left out: %-format strings as written,
    f-strings as templates. Read from the source, so a module another agent is editing need not import."""
    tree = ast.parse((PRODUCTION / path).read_text())
    skipped = {id(node.value) for node in ast.walk(tree) if isinstance(node, ast.Expr)}
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            skipped |= {id(value) for value in node.values}
    found = []
    for node in ast.walk(tree):
        if id(node) in skipped:
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and anchor in node.value:
            found.append(node.value)
        elif isinstance(node, ast.JoinedStr) and anchor in (text := template(node)):
            found.append(text)
    assert found, f'inventory_tracking/{path} says no line with {anchor!r}: reworded? Change logwords.py with it'
    return found


def one(path: str, anchor: str) -> str:
    (found,) = produced(path, anchor)
    return found


def said(text: str) -> str:
    """A `run.say` line as the runner logs it (runner.py MacroRunner._say)."""
    tree = ast.parse((PRODUCTION / 'macros' / 'runner.py').read_text())
    (say,) = (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_say')
    (call,) = (
        n for n in ast.walk(say) if isinstance(n, ast.Call) and getattr(n.func, 'attr', None) == 'info'
    )  # LOG.info
    return literal(call.args[0]) % text


def logged(message: str, level: int = logging.INFO) -> str:
    """The line the log file holds for a message (common.py `log_to_file`'s format)."""
    (form,) = set(produced('common.py', '%(asctime)s'))
    record = logging.makeLogRecord({'msg': message, 'levelno': level, 'levelname': logging.getLevelName(level)})
    return logging.Formatter(form).format(record)


def test_the_logs_stamp_reads() -> None:
    assert logwords.stamp(logged('Macro: Loop on')) is not None


def test_a_leg_line_from_the_loop() -> None:
    form = one('macros/loop.py', 'Loop: game ')
    line = logged(said(form.format(57, 'the chests')))
    found = logwords.LEG.search(line)
    assert found is not None
    assert found.groups() == ('57', 'the chests')


@pytest.mark.parametrize(('text', 'word'), [('Loop on', 'LOOP_ON'), ('Loop off', 'LOOP_OFF')])
def test_the_loop_switched_by_kp6(text: str, word: str) -> None:
    assert text in produced('macros/runner.py', text)
    assert getattr(logwords, word) in logged(said(text))


def test_the_loop_resumed_by_a_restart() -> None:
    (text,) = (s for s in produced('macros/running/watch.py', 'Loop resumed') if s.startswith('Loop resumed'))
    assert logwords.LOOP_RESUMED in logged(said(text))
    form = one('macros/runner.py', 'resumed after a restart: loop')
    for state in ('on', 'off'):
        line = logged(form % (state, 'sure valuables', 'Andariel'))
        found = logwords.RESUMED.search(line)
        assert found is not None
        assert found.groups() == (state, 'Andariel')
        assert (logwords.RESUMED_ON if state == 'on' else logwords.RESUMED_OFF) in line
        assert logwords.RESUMED_ANY in line


def test_the_players_press() -> None:
    form = one('macros/runner.py', 'Macro: request %s, ')
    assert logwords.REQUEST_LOOP in logged(form % ('loop', 0, 'loop'))


def test_the_run_kind_chosen() -> None:
    form = one('macros/runner.py', 'Loop run: ')
    found = logwords.KIND.search(logged(said(form.format('Andariel'))))
    assert found is not None
    assert found.group(1) == 'Andariel'


def test_the_loop_stopped_with_a_valuable_on_the_ground() -> None:
    why = one('macros/running/recovery.py', 'the loop stops here').format('Ring was not picked up', 'Ring')
    line = logged(one('macros/running/recovery.py', 'Macro: loop stopped: ') % why)
    found = logwords.STOPPED.search(line)
    assert found is not None
    assert found.group(1) == why
    assert logwords.STOPS_HERE in line
    assert logwords.LOOP_STOPPED in line
    assert logwords.EVENT.search(line) is not None
    assert logwords.NOW.search(line) is not None


def test_the_game_is_left_and_the_loop_goes_on() -> None:
    line = logged(
        one('macros/running/recovery.py', 'the game is left and the loop goes on') % 'the waypoint is not in view'
    )
    found = logwords.LEFT.search(line)
    assert found is not None
    assert found.group(1) == 'the waypoint is not in view'
    assert logwords.GAME_LEFT in line
    assert logwords.EVENT.search(line) is not None
    assert logwords.NOW.search(line) is not None


@pytest.mark.parametrize(
    ('name', 'quality', 'flags', 'taken', 'label', 'groups'),
    [
        ('Ring', 4, 0, 'material', None, ('magic', 'Ring', None, None, None, '22562', '9539', 'material')),
        (
            'Broad Axe',
            3,
            ETHEREAL_FLAG | SOCKETED_FLAG,
            None,
            None,
            ('superior', 'Broad Axe', ' eth', ' socketed', None, '22562', '9539', None),
        ),
        (
            'Assault Helmet',
            4,
            0,
            'shown',
            'Magic Assault Helmet',
            ('magic', 'Assault Helmet', None, None, 'Magic Assault Helmet', '22562', '9539', 'shown'),
        ),
        ('Jewel', 7, 0, 'unique', 'Jewel', ('unique', 'Jewel', None, None, None, '22562', '9539', 'unique')),
    ],
)
def test_a_census_line_from_the_world(name, quality, flags, taken, label, groups) -> None:
    form = one('game/memory.py', 'Macro: ground: ')
    line = logged(form % census(name, quality, flags, (22561.6, 9539.2), taken, label))
    found = logwords.GROUND.search(line)
    assert found is not None
    assert found.groups() == groups


def test_a_pickup_line_names_the_item() -> None:
    clicked = one('macros/pickup.py', 'Macro: picked up %s %.2fs after the click %s')
    late = one('macros/pickup.py', 'after the click, late')
    for line in (
        logged(clicked % ('Small Charm', 0.08, (0, -24), 0.7, (4, 1235397469))),
        logged(late % ('Small Charm', 1.18, 22553.0, 9560.0)),
    ):
        found = logwords.PICKED.search(line)
        assert found is not None
        assert found.group(1) == 'Small Charm'


def test_the_pickups_choice_and_aims() -> None:
    tree = ast.parse((PRODUCTION / 'macros' / 'pickup.py').read_text())
    (call,) = (
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and n.args
        and isinstance(n.args[0], ast.Constant)
        and str(n.args[0].value).startswith('Macro: pickup: %d drops')
    )
    (choice,) = (template(n) for n in ast.walk(call) if isinstance(n, ast.JoinedStr) and ' at (' in template(n))
    line = logged(
        literal(call.args[0]) % (3, 'healing, valuable', (0, 0), 1751, 1751, choice.format('Ring', 22553.4, 9560.0))
    )
    found = logwords.AIMED.search(line)
    assert found is not None
    assert found.groups()[:3] == ('Ring', '22553', '9560')
    chosen = logwords.PICKUP.search(line)
    assert chosen is not None
    assert chosen.group(1) == 'Ring'
    aims = one('macros/pickup.py', 'Macro: aims for ')
    line = logged(aims % ('Jewel', 1235397469, 22553.0, 9560.0, 1, 2, '(0, -24) wanted [flag 0x101] clicked'))
    found = logwords.AIMED.search(line)
    assert found is not None
    assert found.groups()[3:] == ('Jewel', '22553.0', '9560.0')


@pytest.mark.parametrize(
    ('path', 'anchor'), [('macros/stash.py', 'stack is full'), ('macros/visit.py', 'put down: its stack')]
)
def test_a_full_stack_names_its_kind(path: str, anchor: str) -> None:
    """Both lines name the kind alone (2026-10-18: visit.py's was read as 'Perfect Ruby put down: its')."""
    (form,) = (s for s in produced(path, anchor) if s.startswith('Macro: stash: the %s'))
    found = logwords.FULL.search(logged(form % 'Perfect Ruby'))
    assert found is not None
    assert found.group(1) == 'Perfect Ruby'


@pytest.mark.parametrize(('path', 'anchor'), [('macros/junk.py', 'items identified'), ('macros/cain.py', 'identified')])
def test_identified_by_the_tome_or_cain(path: str, anchor: str) -> None:
    (form,) = (s for s in produced(path, anchor) if s.startswith('Macro: '))
    found = logwords.IDENTIFIED.search(logged(form % (6, 7)))
    assert found is not None
    assert found.groups() == ('6', '7')


def test_an_appraisal() -> None:
    form = one('macros/running/legs.py', 'identify: appraised')
    found = logwords.APPRAISED.search(logged(form % ('magic Large Charm (619)', 3, 0, 'vendor')))
    assert found is not None
    assert found.groups() == (None, 'magic', 'Large Charm', '619', 'vendor')


def test_a_sale_and_the_gold() -> None:
    form = one('macros/shop.py', 'the item %d at (%d, %d)%s')
    line = logged(form % ('sold', 658, 4, 1, ' for 962 gold', 'magic Jewel (658)'))
    found = logwords.SOLD.search(line)
    assert found is not None
    assert found.groups() == ('658', '962', 'magic Jewel (658)')
    assert logwords.DID.search(line) is not None
    assert logwords.NOW.search(line) is not None
    unsold = logwords.UNSOLD.search(logged(form % ('could not sell', 669, 2, 3, '', 'white Ral Rune (669)')))
    assert unsold is not None
    assert unsold.group(1) == '669'
    after = logwords.AFTER.search(logged(one('macros/shop.py', 'after the sales') % (500083, 507731)))
    assert after is not None
    assert after.groups() == ('500083', '507731')
    keys = logged(one('macros/shop.py', 'Macro: shop: keys %s') % (17, 17, 0, 0, '', 20, 20))
    assert logwords.NOTE.search(keys) is not None
    assert logwords.DID.search(keys) is not None


def test_a_repair() -> None:
    """repair.py says the most worn item too since 8accb7d: the old pattern missed every repair after it."""
    form = one('macros/repair.py', 'repair: the staff')
    line = logged(form % (9, 69, 69, '12/40 (class 123)', '40/40 (class 123)', 254382, 152270))
    found = logwords.REPAIRED.search(line)
    assert found is not None
    assert found.groups() == ('9', '69', '254382', '152270')
    assert logwords.NOW.search(line) is not None


def test_the_trade_sessions_report() -> None:
    tree = ast.parse((PRODUCTION / 'macros' / 'visit.py').read_text())
    (stops,) = (
        ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign) and any(getattr(t, 'id', None) == 'STOPS' for t in n.targets)
    )
    took = {'cain': 3.5, 'stash': 12.7, 'jamella': 8.4, 'walk': 2.9}
    done = ', '.join(f'{stop} {took[stop]:.1f}' if stop in took else f'{stop} -' for stop in stops)
    form = one('macros/visit.py', 'trade session done')
    line = logged(form % ('', 0, 2, 4, 'free', 9, 0, 17, 'from the Sling', '?', 'clear', 27.6, done))
    found = logwords.VISIT_STOPS.search(line)
    assert found is not None
    assert found.groups() == ('3.5', '8.4')
    assert logwords.NOW.search(line) is not None


def test_the_stash_by_the_view() -> None:
    form = one('macros/visit.py', 'by the view: %d items put in')
    line = logged(form % (6, '2,4', 0, 0, 2, 12.6))
    assert logwords.DID.search(line) is not None
    assert logwords.NOTE.search(line) is not None


def test_the_cube_moved() -> None:
    (form,) = (s for s in produced('macros/cube.py', 'moved in') if s.startswith('Macro: cube: '))
    line = logged(form % (4, 4))
    assert logwords.DID.search(line) is not None
    assert logwords.NOTE.search(line) is not None


def test_a_teleport_and_the_andariel_marks() -> None:
    assert logwords.TELEPORT in logged(said(one('macros/teleport.py', 'Teleport toward ').format('Ring', 0, '')))
    assert logwords.CREATING.search(logged(said(one('macros/routines.py', 'Creating ').format('cyberr4'))))
    assert logwords.GAME_LOADED in logged(one('macros/routines.py', 'game loaded') % 5.15)
    assert logged(said('Save and Exit')).endswith(logwords.SAVE_AND_EXIT)
    assert 'Save and Exit' in produced('macros/routines.py', 'Save and Exit')
    kill = one('terror/bosses.py', 'Boss kill: ') % ('Andariel', 284)
    assert logwords.KILL.search(logged(kill))
    opened = logwords.OPENED.search(logged(one('takes/record.py', 'opened in area') % ('20261018T125836Z-37', 37)))
    assert opened is not None
    assert opened.groups() == ('20261018T125836Z-37', '37')


def experience_lines() -> list[str]:
    """A terror zone game's experience lines as experience.py writes them and loop.py says them (`say_experience`)."""
    from inventory_tracking.macros.experience import Ledger, Reading

    form = 'Macro: %s'
    assert form in produced('macros/loop.py', form)
    ledger = Ledger()
    ledger.look('cyber5', 103, Reading(2_000_000, 94), 0.0)
    ledger.look('cyber5', 108, Reading(2_000_000, 94), 60.0)
    lines = ledger.game_over(3, Reading(3_234_567, 95), 600.0)
    return [logged(form % line) for line in lines]


def test_the_experience_of_a_tz_game_and_its_levels() -> None:
    level, game = experience_lines()
    found = logwords.EXPERIENCE_LEVEL.search(level)
    assert found is not None
    assert found.groups() == ('The Chaos Sanctuary', '+1,234,567', '540', '95')
    assert logwords.EXPERIENCE_GAME.search(level) is None
    found = logwords.EXPERIENCE_GAME.search(game)
    assert found is not None
    number, gain, at, nxt, rate, over = found.groups()
    assert (number, gain, at, rate, over) == ('3', '+1,234,567', '95', '7,407,402', '1')
    assert logwords.amount(nxt) == 2717422497 - 3_234_567
    assert logwords.amount('-1,000') == -1000
    assert logwords.EXPERIENCE_LEVEL.search(game) is None


def test_games_and_watch_report_a_tz_games_experience(tmp_path: Path, capsys) -> None:
    lines = [
        '2026-10-19 22:00:00,000 INFO Macro: Loop: game 3, TZ level',
        '2026-10-19 22:09:00,000 INFO Macro: Loop: game 3, Save and Exit',
        *experience_lines(),
        '2026-10-19 22:10:00,000 INFO Macro: Loop: game 4, next game',
    ]
    session = tmp_path / '20261019T190000Z-test'
    session.mkdir()
    (session / 'probe.log').write_text('\n'.join(lines) + '\n')
    told = games.read(session, None, None)[0]
    assert (told[0].experience, told[0].rate) == (1_234_567, '7,407,402')
    assert told[0].levels == [('The Chaos Sanctuary', 1_234_567, 540)]
    summary = games.experience(told)
    assert summary is not None
    assert (summary['games'], summary['an_hour'], summary['loop_rate']) == (1, 7_407_402, '7,407,402')
    assert summary['levels_a_minute']['The Chaos Sanctuary']['a_minute'] == round(60 * 1_234_567 / 540)
    out = missed_by_watch(lines, capsys)
    assert 'game 3: 600s, +1,234,567 exp (' in out


def test_watch_sums_a_leg_over_its_stretches(capsys) -> None:
    """A leg that comes back counts every stretch, not the span from its first start (game 2, 22:39-22:45 on
    2026-10-19: 'TZ Town Portal 164s' was the waypoint and the next level's time)."""
    lines = [
        '2026-10-19 22:00:00,000 INFO Macro: Loop: game 3, TZ level',
        '2026-10-19 22:00:30,000 INFO Macro: Loop: game 3, TZ next level',
        '2026-10-19 22:00:40,000 INFO Macro: Loop: game 3, TZ level',
        '2026-10-19 22:01:10,000 INFO Macro: Loop: game 3, TZ Town Portal',
        '2026-10-19 22:01:15,000 INFO Macro: Loop: game 3, TZ next level',
        '2026-10-19 22:01:20,000 INFO Macro: Loop: game 4, next game',
    ]
    out = missed_by_watch(lines, capsys)
    assert 'game 3: 80s (chests 0s, TZ level 60s)' in out


def test_watch_stalls_only_when_a_leg_does_nothing() -> None:
    """A TZ level's leg runs minutes while it teleports and kills: no STALL then; a quiet one or one past LONG_LEG is
    (game 2 and 4, 22:41-22:53 on 2026-10-19: STALLs while it explored room by room)."""
    lines = [
        '2026-10-19 22:41:48,720 INFO Macro: Loop: game 2, TZ next level',
        '2026-10-19 22:43:00,000 INFO Macro: teleport aimed at (5188.1, 3312.9), 26.6 from (5191.5, 3286.5), 0.0 off'
        ' the way, footing True, 173 grids, pointer (2072, 1133) in (1920, 0, 2560, 1418); landed at (5188.5, 3313.5)',
        '2026-10-19 22:43:10,000 INFO Macro: Nothing left in reach: 7 down in 1 casts',
    ]
    assert all(logwords.PROGRESS.search(line) for line in lines[1:])
    assert not logwords.PROGRESS.search('2026-10-19 22:43:10,000 INFO Macro: Yielded (the key asks): 0 down in 1 casts')
    shown = watch.Watch(stall=75.0, again=120.0)
    shown.loud = False
    for line in lines:
        shown.line(line)
    last = watch.stamp(lines[-1])
    assert last is not None
    t = last.timestamp()
    assert not shown.stalled(t + 60)
    assert shown.stalled(t + 80)
    leg = watch.stamp(lines[0])
    assert leg is not None
    shown.last_progress_wall = leg.timestamp() + watch.LONG_LEG
    assert shown.stalled(leg.timestamp() + watch.LONG_LEG + 1)


def test_watch_takes_the_loops_own_wait_for_no_stall() -> None:
    """The next terror zone's wait (loop.py `leg`, tzloop.py `zone_wait`): STALLs every 2 min while the loop stood in
    town on purpose (03:35 on 2026-10-20); counted again once the wait is over."""
    line = '2026-10-20 03:34:19,640 INFO Macro: loop: waiting 1560 s before the next leg (the next terror zone)'
    source = (ROOT / 'inventory_tracking' / 'macros' / 'loop.py').read_text()
    assert "'Macro: loop: waiting %.0f s before the next leg (the next terror zone)'" in source
    shown = watch.Watch(stall=75.0, again=120.0)
    shown.loud = False
    shown.line('2026-10-20 03:30:08,000 INFO Macro: Loop: game 42, next game')
    shown.line(line)
    at = watch.stamp(line)
    assert at is not None
    t = at.timestamp()
    assert not shown.stalled(t + 600)
    assert not shown.stalled(t + 1560 + 60)
    assert shown.stalled(t + 1560 + 80)


# --- The tools hold no line pattern of their own ---------------------------------------------------------------------


@pytest.mark.parametrize('tool', sorted(p.name for p in TOOLS.glob('*.py') if p.name != 'logwords.py'))
def test_a_tool_reads_lines_through_logwords(tool: str) -> None:
    """No string literal of a tool (docstrings aside) names a log line's words: they are logwords.py's."""
    tree = ast.parse((TOOLS / tool).read_text())
    docstrings = {id(node.value) for node in ast.walk(tree) if isinstance(node, ast.Expr)}
    own = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
        and ('Macro: ' in node.value or 'Macro stopped' in node.value or 'Combat take' in node.value)
    ]
    assert own == []


# --- The click rule watch.py and games.py share (games.clicked) ------------------------------------------------------

GAME = [
    '2026-10-18 15:02:40,000 INFO Macro: Loop: game 7, the chests',
    '2026-10-18 15:02:50,000 INFO Macro: ground: magic Jewel at (22553, 9560): taken (material)',
    '2026-10-18 15:02:55,000 INFO Macro: pickup: 1 drops (valuable), belt short (0, 0), life 1751/1751; Jewel at '
    '(22553, 9560)',
    '2026-10-18 15:02:56,000 INFO Macro: aims for Jewel (unit 1) at (22553.0, 9560.0), 1 wanted and 0 other drops: '
    '(0, -24) wanted [flag 0x101 type 4 id 1 tail 0x160016] clicked',
    '2026-10-18 15:02:56,100 INFO Macro stopped: priced act expired',
    '2026-10-18 15:03:10,000 INFO Macro: Loop: game 8, next game',
]


def unpicked_by_games(lines: list[str], tmp_path: Path) -> list:
    session = tmp_path / '20261018T120000Z-test'
    session.mkdir()
    (session / 'probe.log').write_text('\n'.join(lines) + '\n')
    return [(item.name, why) for item, why in games.read(session, None, None)[3] if not item.picked]


def missed_by_watch(lines: list[str], capsys: pytest.CaptureFixture[str]) -> str:
    seen = watch.Watch(1e9, 1e9)
    seen.full = set()
    for line in lines:
        seen.line(line)
    return capsys.readouterr().out


def test_a_clicked_item_the_census_never_saw_again_is_taken(tmp_path: Path, capsys) -> None:
    assert unpicked_by_games(GAME, tmp_path) == []
    assert 'MISSED' not in missed_by_watch(GAME, capsys)


def test_an_item_never_clicked_is_missed(tmp_path: Path, capsys) -> None:
    unclicked = [line for line in GAME if 'aims for' not in line]
    assert unpicked_by_games(unclicked, tmp_path) == [('Jewel', 'a gem, charm or jewel the read listed')]
    assert 'MISSED: game 7, magic Jewel at (22553, 9560)' in missed_by_watch(unclicked, capsys)


def test_an_item_the_census_saw_after_the_click_is_missed(tmp_path: Path, capsys) -> None:
    again = [*GAME[:5], GAME[1].replace('15:02:50', '15:02:58'), GAME[5]]
    assert unpicked_by_games(again, tmp_path) == [('Jewel', 'a gem, charm or jewel the read listed')]
    assert 'MISSED' in missed_by_watch(again, capsys)


def test_a_full_stack_put_down_is_no_miss(tmp_path: Path) -> None:
    """visit.py's put-down line counts the kind full, so a Perfect Ruby left on the ground is by design."""
    lines = [
        '2026-10-18 15:02:40,000 INFO Macro: Loop: game 7, the chests',
        '2026-10-18 15:02:41,000 INFO Macro: stash: the Perfect Ruby put down: its stack is full and no vendor buys it',
        '2026-10-18 15:02:50,000 INFO Macro: ground: normal Perfect Ruby at (22553, 9560): taken (material)',
        '2026-10-18 15:03:10,000 INFO Macro: Loop: game 8, next game',
    ]
    assert unpicked_by_games(lines, tmp_path) == [('Perfect Ruby', None)]


def test_trade_counts_cains_identification(tmp_path: Path) -> None:
    session = tmp_path / '20261018T120000Z-test'
    session.mkdir()
    (session / 'probe.log').write_text(
        '2026-10-18 15:59:40,000 INFO Macro: Loop: game 3, town visit\n'
        '2026-10-18 15:59:47,997 INFO Macro: Cain: 7 of 7 items identified\n'
        '2026-10-18 16:00:47,997 INFO Macro: identify: 1 of 2 items identified\n'
    )
    found = trade.read(session, logwords.stamp('2026-10-18 15:00:00,000'), logwords.stamp('2026-10-18 17:00:00,000'))
    assert found['tries'] == [8, 9]


def test_watch_reports_off_every_minute_even_with_fresh_manual_game_logs(tmp_path, monkeypatch, capsys):
    log = tmp_path / 'probe.log'
    log.write_text('manual game activity\n')
    clock = [100.0]
    monkeypatch.setattr(watch.time, 'monotonic', lambda: clock[0])
    seen = watch.Watch(75, 120)
    seen.health(log)
    assert 'loop off' in capsys.readouterr().out
    clock[0] = 159.0
    seen.health(log)
    assert capsys.readouterr().out == ''
    clock[0] = 160.0
    seen.health(log)
    assert 'loop off' in capsys.readouterr().out
    assert not seen.on


def test_watch_does_not_report_old_loop_on_as_active(tmp_path, capsys):
    log = tmp_path / 'probe.log'
    log.write_text('old session\n')
    seen = watch.Watch(75, 120)
    seen.line('2026-10-18 15:02:40,000 INFO Macro: Loop: game 7, the chests')
    seen.health(log)
    assert 'stalled' in capsys.readouterr().out


def test_watch_reports_missing_evidence_without_claiming_service_dead(tmp_path, capsys):
    seen = watch.Watch(75, 120)
    seen.health(tmp_path / 'missing.log')
    assert 'unavailable' in capsys.readouterr().out
