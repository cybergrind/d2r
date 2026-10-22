"""The boss ledger (macros/bossledger.py): the macros' view of the terror tracker's boss book, the one record of a
game's bosses (the player, 2026-10-22: "we need to kill all bosses, no exceptions to that"; "<game-id>-<level> as
key")."""

import ast
import json
import re
from pathlib import Path

from inventory_tracking.game.layout import SUPER_FLAG
from inventory_tracking.game.records import Monster
from inventory_tracking.levels.model import Room
from inventory_tracking.macros.bossledger import BossLedger, expected, game_key
from inventory_tracking.macros.loop import GameId
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.terror.tracker import BOOK_SECONDS, ZoneTracker


GAME = GameId('cyberr16', 432287142)
DURANCE_3 = 102
COUNCIL = Room(796, 600, 200, 24, 24, variant=0, block=(600, 200, 24, 24))  # Act 3 - Mephisto Complex


def ledger(tracker: ZoneTracker | None = None) -> tuple[BossLedger, ZoneTracker]:
    tracker = tracker if tracker is not None else ZoneTracker()
    found = BossLedger()
    found.begin(GAME)
    found.attach(tracker.killed)  # as routes/progress.py `Progress.dead` hands it
    return found, tracker


def test_the_game_id_is_the_name_and_the_player_unit_id():
    assert game_key(GAME) == 'cyberr16#432287142'
    assert game_key('cyberr16') == 'cyberr16'
    assert game_key(None) is None


def test_the_bosses_of_a_level_before_it_is_read_are_the_catalogues_fights_and_the_scripts():
    chaos = dict(expected(108))
    assert chaos['Diablo'] == 'route'
    assert {'Grand Vizier of Chaos', 'Lord De Seis', 'Infector of Souls'} <= set(chaos)
    throne = dict(expected(131))
    assert {'Colenzo the Annihilator', 'Lister the Tormentor'} <= set(throne)
    assert dict(expected(132)) == {'Baal': 'route'}
    assert expected(107) == ()  # the River of Flame: Hephasto only once its rooms are read


def test_the_council_is_read_from_durance_3s_rooms_at_its_spots_and_a_super_unique_there_is_taken_for_it():
    found, tracker = ledger()
    found.plan((DURANCE_3,))
    assert {boss.name for boss in found.alive_in(DURANCE_3)} == {'Mephisto'}
    found.rooms(DURANCE_3, [COUNCIL])
    bosses = {boss.name: boss for boss in found.alive_in(DURANCE_3)}
    assert set(bosses) == {'Mephisto', 'Bremm Sparkfist', 'Maffer Dragonhand', 'Wyand Voidbringer'}
    spot = (600 * TILE_UNITS + 103, 200 * TILE_UNITS + 123)
    assert bosses['Maffer Dragonhand'].place == spot
    assert bosses['Maffer Dragonhand'].known_by == 'rooms'
    # 19:53:03 on 2026-10-21: "target the elite 347", then out of the read 84 away: taken, then followed
    maffer = Monster(3110582129, 347, 1, spot[0] + 6, spot[1] - 4, flags=SUPER_FLAG)
    plain = Monster(7, 347, 1, spot[0] + 2, spot[1], flags=0)
    found.sight(DURANCE_3, [plain, maffer])
    taken = {boss.name: boss for boss in found.alive_in(DURANCE_3)}['Maffer Dragonhand']
    assert (taken.unit, taken.seen) == (3110582129, True)
    found.sight(DURANCE_3, [])  # out of the read: its last place kept, any distance
    assert {boss.name: boss for boss in found.alive_in(DURANCE_3)}['Maffer Dragonhand'].unit == 3110582129
    tracker.slain = frozenset({'Mephisto', 'Maffer Dragonhand'})
    assert {boss.name for boss in found.alive_in(DURANCE_3)} == {'Bremm Sparkfist', 'Wyand Voidbringer'}


def test_without_a_tracker_nothing_is_alive_and_nothing_is_kept():
    found = BossLedger()
    found.begin(GAME)
    found.attach(None)
    found.plan((132,))
    assert found.alive() == []
    found.attach(lambda: frozenset())  # a plain callable is no book
    assert found.alive() == []


def test_the_book_is_keyed_game_and_level_written_atomically_and_read_back_by_a_restarted_service(tmp_path):
    store = tmp_path / 'terror-games.json'
    found, _ = ledger(ZoneTracker(store, wall=lambda: 1000.0))
    found.plan((132,))
    found.rooms(DURANCE_3, [COUNCIL])
    held = json.loads(store.read_text(encoding='utf-8'))
    assert set(held['bosses']) == {'cyberr16#432287142-132', 'cyberr16#432287142-102'}
    assert 'Baal' in held['bosses']['cyberr16#432287142-132']
    assert not list(tmp_path.glob('*.part'))  # the file beside it renamed over it
    # A restart: the same game's records back, another game's apart
    again, _ = ledger(ZoneTracker(store, wall=lambda: 2000.0))
    assert {boss.name for boss in again.alive()} == {boss.name for boss in found.alive()}
    other = BossLedger(ZoneTracker(store, wall=lambda: 2000.0))
    other.begin(GameId('cyberr16', 99))  # the name come round again: another game
    assert other.alive() == []
    # A day later: dropped
    late = ZoneTracker(store, wall=lambda: 1000.0 + BOOK_SECONDS + 1)
    assert late.book == {}


def test_the_trackers_own_save_keeps_the_book(tmp_path):
    store = tmp_path / 'terror-games.json'
    tracker = ZoneTracker(store, wall=lambda: 1000.0)
    found, _ = ledger(tracker)
    found.plan((132,))
    tracker.game_levels = {131: 'aa' * 8}
    tracker.save()
    held = json.loads(store.read_text(encoding='utf-8'))
    assert held['games']
    assert 'cyberr16#432287142-132' in held['bosses']


# The one-object rule (the player, of the stash: "one object that is used everywhere ... no copies, no stale
# records"): the boss records live in the tracker's book only; the ledger keeps none of its own
MACROS = Path(__file__).parents[3] / 'inventory_tracking'


def stub(node: ast.FunctionDef) -> bool:
    """A Protocol's `...` body (bossledger.py `Book`): no writer."""
    return len(node.body) == 1 and isinstance(node.body[0], ast.Expr) and node.body[0].value.__class__ is ast.Constant


def test_nothing_else_keeps_boss_state():
    ledger_fields = set(vars(BossLedger()))
    assert ledger_fields == {'book', 'game'}
    writers = []
    for path in MACROS.rglob('*.py'):
        source = path.read_text(encoding='utf-8')
        if 'boss_note(' not in source and 'def boss_note' not in source:
            continue
        tree = ast.parse(source)
        defines = any(
            isinstance(node, ast.FunctionDef) and node.name == 'boss_note' and not stub(node) for node in ast.walk(tree)
        )
        if defines:
            writers.append(path.relative_to(MACROS).as_posix())
    assert writers == ['terror/tracker.py']
    # tzloop's own list of boss levels (Baal's, 10-22 morning) gone for the ledger; routines.py BOSS_LEVELS (the
    # KP_1 level run's boss levels) is no record of a game
    names = re.compile(r'^(BOSS_LEVELS = \{|\s*self\.(boss_records|bosses_alive|bosses_seen) =)', re.MULTILINE)
    for path in MACROS.rglob('*.py'):
        found = names.findall(path.read_text(encoding='utf-8'))
        assert not found, (path, found)
