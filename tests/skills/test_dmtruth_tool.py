"""The Teleport -> Death Mark ground truth of a combat take (the d2-loop-watch skill's tools/dmtruth.py, 2026-10-24):
the landing, the mark's key, its cast and its state on the monster from the game's own state.

The player, 2026-10-24 ~19:24: "I'm very sure that something is 1sec off ... we need to make sure that you actually also
can measure it: the real delay".
"""

import gzip
import importlib
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / '.agents' / 'skills' / 'd2-loop-watch' / 'tools'
sys.path.insert(0, str(TOOLS))
dmtruth = importlib.import_module('dmtruth')

NO_OWNER = 4294967295
PLAYER = 7
HERALD_MEMBER, NEIGHBOUR = 50, 51
STEP = 0.04  # 25 frames a second
START = 100.0


def words(*states: int) -> str:
    """Eight state words (states 0-255) with `states` set, as the recorder writes them (hex)."""
    raw = bytearray(32)
    for state in states:
        raw[state // 8] |= 1 << (state % 8)
    return raw.hex()


def skill(skill_id: int) -> str:
    return skill_id.to_bytes(2, 'little').hex() + '00' * 18


class Play:
    """A synthetic take, frame by frame: the character's mode and place, the monsters, the inputs."""

    def __init__(self) -> None:
        self.frames: list[dict] = []
        self.events: list[dict] = []
        self.records: list[dict] = []
        self.mode, self.x, self.y = 1, 1000.0, 1000.0
        self.marked: dict[int, bool] = {HERALD_MEMBER: False, NEIGHBOUR: False}
        self.hovered: list | None = [1, HERALD_MEMBER]
        self.t = START

    def frame(self, mode: int | None = None, cast_skill: int | None = None) -> float:
        """One frame at the next tick; a new cast's mode writes the character's record row with its skill."""
        before = self.mode
        self.mode = before if mode is None else mode
        n = len(self.frames) + 1
        monsters = [
            [HERALD_MEMBER, 310, 1, self.x + 6.0, self.y - 6.0, 128, 1000, 0, NO_OWNER, 0],
            [NEIGHBOUR, 310, 1, self.x + 8.0, self.y - 4.0, 128, 1000, 0, NO_OWNER, 0],
        ]
        line = {
            't': round(self.t, 3),
            'n': n,
            'late': 0,
            'p': [PLAYER, self.mode, 108, self.x, self.y, 390, 388, 2000, 2000, 500, 500],
            'm': monsters,
            'in': [800, 300, 16, 0.5, 0.36, []],
            'rect': [0, 0, 1600, 900],
            'k': (b'\0' * 8 + int(self.t * 1000).to_bytes(4, 'little') + b'\0' * 20).hex(),
            'h': self.hovered,
        }
        self.frames.append(line)
        rows = []
        if self.mode != before:
            rows.append([PLAYER, '00' * 16, '', skill(cast_skill) if cast_skill else ''])
        for unit, on in self.marked.items():
            rows.append([unit, '00' * 16, words(212) if on else words(), ''])
        self.records.append({'t': round(self.t, 3), 'n': n, 'u': rows})
        at = self.t
        self.t += STEP
        return at

    def sent(self, name: str, down: bool, at: float | None = None) -> None:
        code = {'t': 28, 'd': 40}[name]
        t = self.t - STEP / 2 if at is None else at
        self.events.append(
            {'t': round(t, 3), 'event': 'sent', 'input': 'key', 'code': code, 'down': down, 'name': name}
        )

    def log(self, text: str, at: float | None = None) -> None:
        self.events.append({'t': round(self.t - STEP / 2 if at is None else at, 3), 'event': 'log', 'text': text})

    def hop(self, units: float = 10.0) -> float:
        """A Teleport: the key, its cast (7 frames), the position jumping in its 8th frame, the cast's end."""
        self.sent('t', True)
        self.log('Macro: Teleport on t, player mode 1')
        self.frame(10, 54)
        for _ in range(6):
            self.frame()
        self.x += units
        self.log('Macro: teleport aimed at (1010, 1000); landed at (1010, 1000)')
        jump = self.frame()
        self.frame(1)
        return jump

    def mark(self, aimed: int, lands_on: int | None, frames_before: int = 8) -> float:
        """The mark's key and its cast; its state on `lands_on` 7 frames (280 ms) after the cast's start."""
        for _ in range(frames_before):
            self.frame()
        self.log("Macro: mark: designated the monster 310 (50), 90/128: the tier 5 Herald pack's member")
        self.log('Macro: Death Mark on d, player mode 1')
        self.sent('d', True)
        key = self.t - STEP / 2
        self.frame(10, 375)
        self.log(f'Macro: Death Mark on the monster 310 ({aimed}), 128/128')
        self.sent('d', False)
        for i in range(7):
            if i == 6 and lands_on is not None:
                self.marked[lands_on] = True
            self.frame()
        self.frame(1)
        return key

    def write(self, base: Path, name: str = '20261024T161813Z-108') -> Path:
        directory = base / name
        directory.mkdir(parents=True)
        manifest = {'clock': {'monotonic': START, 'wall': 1792858800.0}, 'area': 108, 'keys': {'28': 't', '40': 'd'}}
        (directory / 'manifest.json').write_text(json.dumps(manifest))
        events = sorted(self.events, key=lambda e: e['t'])
        for file, rows in (('frames.jsonl', self.frames), ('events.jsonl', events), ('records.jsonl', self.records)):
            with gzip.open(directory / f'{file}.gz', 'wt') as handle:
                handle.writelines(json.dumps(row) + '\n' for row in rows)
        return directory


def read(directory: Path) -> tuple:
    truth = dmtruth.load(directory)
    keys = dmtruth.keys_of(truth)
    return truth, keys, dmtruth.landings(truth, keys)


def test_the_game_data_names_the_ids() -> None:
    """Death Mark's state and the skills by the installed game's tables, never from memory (AGENTS.md rule 3)."""
    excel = ROOT / 'pricing' / 'raw' / 'game-excel'
    if not (excel / 'states.txt').exists():
        pytest.skip('the game tables are not in this tree')
    states = {r.split('\t')[0]: int(r.split('\t')[1]) for r in (excel / 'states.txt').read_text().splitlines()[1:]}
    assert states['death_mark'] == dmtruth.MARK_STATE
    skills = {r.split('\t')[0]: r.split('\t')[1] for r in (excel / 'skills.txt').read_text().splitlines()[1:]}
    assert [int(skills[name]) for name in ('Teleport', 'Blade Warp', 'Death Mark')] == [
        dmtruth.TELEPORT,
        dmtruth.BLADE_WARP,
        dmtruth.DEATH_MARK,
    ]


def test_a_state_word_is_read_little_endian_from_the_first() -> None:
    assert dmtruth.states_on(bytes.fromhex(words(212)), 212)
    assert not dmtruth.states_on(bytes.fromhex(words(211, 213)), 212)
    assert not dmtruth.states_on(b'\0' * 8, 212)


def test_a_landing_gives_the_mark_key_its_cast_and_its_state(tmp_path: Path) -> None:
    play = Play()
    play.frame()
    jump = play.hop()
    key = play.mark(HERALD_MEMBER, HERALD_MEMBER)
    truth, keys, (row,) = read(play.write(tmp_path))
    assert truth.mark_key == 'd'
    assert [k.outcome for k in keys] == ['took']
    assert (row.hop, row.hops, row.herald, row.ahead, row.outcome) == (1, 1, 5, True, 'took')
    assert row.key == pytest.approx(key - jump, abs=1e-3)
    assert row.mark_cast == pytest.approx(key - jump + STEP / 2, abs=1e-3)  # the cast in the frame after the key
    assert row.state - row.mark_cast == pytest.approx(7 * STEP, abs=1e-3)  # the state 280 ms into the cast
    assert row.cast_end == pytest.approx(STEP, abs=1e-3)  # the Teleport's cast ends a frame after the jump
    assert row.cast_start == pytest.approx(7 * STEP, abs=1e-3)
    assert row.unit == HERALD_MEMBER
    assert not row.wrong
    stages = row.stages()
    assert stages['key->cast'] == 20
    assert stages['cast->state'] == 280
    assert stages['tp cast->state'] == round(1000 * (row.cast_start + row.state))


def test_the_state_on_the_hovered_neighbour_is_a_wrong_target(tmp_path: Path) -> None:
    play = Play()
    play.frame()
    play.hop()
    play.hovered = [1, NEIGHBOUR]
    play.mark(HERALD_MEMBER, NEIGHBOUR)
    _, keys, (row,) = read(play.write(tmp_path))
    assert keys[0].outcome == 'wrong target'
    assert keys[0].hovered == NEIGHBOUR
    assert row.wrong
    assert row.unit == NEIGHBOUR
    assert row.aimed == HERALD_MEMBER


def test_a_cast_on_a_unit_marked_already_and_one_on_nothing(tmp_path: Path) -> None:
    play = Play()
    play.marked[HERALD_MEMBER] = True
    play.frame()
    play.hop()
    play.mark(HERALD_MEMBER, None)
    play.hovered = None
    play.mark(NEIGHBOUR, None, frames_before=30)
    _, keys, rows = read(play.write(tmp_path))
    assert [k.outcome for k in keys] == ['already on', 'no state']
    assert rows[0].stages()['jump->applied'] == round(1000 * (rows[0].mark_cast + dmtruth.CAST_TO_STATE))


def test_a_key_under_a_strike_that_never_casts_is_lost_and_hops_make_one_move(tmp_path: Path) -> None:
    play = Play()
    play.frame()
    first = play.hop()
    play.frame()
    second = play.hop()
    play.frame(10, 388)  # the strike
    play.sent('d', True)
    play.sent('d', False, at=play.t + 0.02)
    for _ in range(8):
        play.frame()
    play.frame(1)
    for _ in range(30):
        play.frame()
    _, keys, rows = read(play.write(tmp_path))
    assert [k.outcome for k in keys] == ['lost']
    assert keys[0].busy == 388
    assert [(r.hop, r.hops) for r in rows] == [(1, 2), (2, 2)]
    assert rows[1].first_jump == pytest.approx(second - first, abs=1e-3)
    assert rows[1].lost == 1
    assert rows[1].between == [388]
    assert not rows[1].ahead
    assert rows[0].keys == 0
    assert rows[0].next_hop is not None


def test_a_mark_chained_in_a_strike_is_dated_by_its_state(tmp_path: Path) -> None:
    play = Play()
    play.frame()
    jump = play.hop()
    play.frame(10, 388)
    play.sent('d', True)
    play.log('Macro: Death Mark on the monster 310 (50), 128/128')
    for i in range(10):
        if i == 7:
            play.marked[HERALD_MEMBER] = True
        play.frame()
    play.frame(1)
    _, keys, (row,) = read(play.write(tmp_path))
    assert keys[0].outcome == 'unseen cast'
    assert not row.cast_seen
    assert row.stages()['cast->state'] is None
    assert row.mark_cast == pytest.approx(row.state - dmtruth.CAST_TO_STATE, abs=1e-3)
    assert row.state > row.key > 0
    assert row.t == pytest.approx(jump, abs=1e-3)


def test_a_record_row_inside_a_cast_naming_another_skill_splits_it() -> None:
    frames = [{'t': 1.0 + i * STEP, 'n': i + 1, 'p': [PLAYER, 10 if 1 <= i <= 12 else 1]} for i in range(15)]
    casts = dmtruth.casts_of(frames, {2: 388}, [(1.04, 388), (1.30, 375)])
    assert [(c.skill, c.chained) for c in casts] == [(388, False), (375, True)]
    assert casts[0].end == casts[1].start == 1.30


def test_the_clocks_agree_on_a_steady_take(tmp_path: Path) -> None:
    play = Play()
    play.frame()
    play.hop()
    play.mark(HERALD_MEMBER, HERALD_MEMBER)
    directory = play.write(tmp_path)
    checks = dmtruth.clocks(dmtruth.load(directory), directory, runs=tmp_path / 'no-sessions')
    low, _, high = checks['game clock - frame clock (p1, p50, p99, ms)']
    assert -1.5 <= low <= high <= 1.5


def path(target: int) -> str:
    """A path record whose target unit (0x7C) is `target`."""
    raw = bytearray(0x80)
    raw[0x7C:0x80] = target.to_bytes(4, 'little')
    return raw.hex()


def test_the_demon_going_for_the_marked_unit_is_read_from_the_paths(tmp_path: Path) -> None:
    play = Play()
    play.frame()
    play.hop()
    play.mark(HERALD_MEMBER, HERALD_MEMBER)
    directory = play.write(tmp_path)
    demon = 90
    shown = next(r['t'] for r in play.records if any(u[0] == HERALD_MEMBER and u[2] == words(212) for u in r['u']))
    with gzip.open(directory / 'frames.jsonl.gz', 'wt') as handle:
        for frame in play.frames:
            frame['m'].append([demon, 744, 1, 1001.0, 1001.0, 128, 500, 0, PLAYER, 0])
            handle.write(json.dumps(frame) + '\n')
    rows = [
        {'t': START, 'n': 1, 'm': [[demon, path(NEIGHBOUR)], [HERALD_MEMBER, path(PLAYER)]]},
        {'t': round(shown + STEP, 3), 'n': 99, 'm': [[demon, path(HERALD_MEMBER)]]},
        {'t': round(shown + 0.5, 3), 'n': 120, 'm': [[HERALD_MEMBER, path(demon)]]},
    ]
    with gzip.open(directory / 'paths.jsonl.gz', 'wt') as handle:
        handle.writelines(json.dumps(row) + '\n' for row in rows)
    _, _, (row,) = read(directory)
    assert row.was_on == 'character'
    assert row.pets_on == pytest.approx(STEP, abs=1e-3)
    assert row.turned == pytest.approx(0.5, abs=1e-3)
