"""The stand after a Teleport, from the game's state (the d2-loop-watch skill's tools/stopwatch.py, 2026-10-24): the
landing, the stand, the casts, Death Mark's cast and its state on a monster, and the demons standing with the
character until a curse sends them.

The player, 2026-10-24 ~20:11: "we already teleported and standing, daemon is with us ... we're not casting DM for an
extended period of time ... measure this real delay first".
"""

import importlib
import json
import struct
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / '.agents' / 'skills' / 'd2-loop-watch' / 'tools'
sys.path.insert(0, str(TOOLS))
stopwatch = importlib.import_module('stopwatch')

STEP = 0.04  # 25 samples a second, as the recorder's frames
WALL = 1_792_862_000.0  # the wall clock at t = 0
CASTING, NEUTRAL = 10, 1
DEFILER, BOUND, MERC = 744, 189, 338
HERALD, MEMBER = 101, 102


class Stream:
    """A synthetic sample stream: the character at (x, y), its pets, two hostiles, a clock that steps."""

    def __init__(self) -> None:
        self.t = 0.0
        self.x, self.y = 100.0, 100.0
        self.mode, self.skill = NEUTRAL, None
        self.pets_at: tuple[float, float] | None = (130.0, 130.0)  # the demons' place (None: with the character)
        self.marked: set[int] = set()
        self.foes_at = {HERALD: (127.0, 100.0), MEMBER: (129.0, 103.0)}
        self.samples: list = []

    def sample(self, frames: int = 1) -> None:
        for _ in range(frames):
            pets_x, pets_y = self.pets_at if self.pets_at is not None else (self.x, self.y)
            foes = tuple(
                stopwatch.Foe(unit, 3, 1, fx, fy, 8 if unit == HERALD else 16, unit in self.marked, 5)
                for unit, (fx, fy) in self.foes_at.items()
            )
            companions = (
                (1, DEFILER, 1, pets_x + 0.1, pets_y),
                (2, BOUND, 1, pets_x, pets_y + 0.1),
                (3, MERC, 1, self.x + 9.0, self.y),
            )
            self.samples.append(
                stopwatch.Sample(
                    self.t, WALL + self.t, 108, self.x, self.y, self.mode, self.skill, 2000, 700, companions, foes
                )
            )
            self.t = round(self.t + STEP, 3)


def run(stream: Stream, lines: list[str] | None = None) -> tuple[list, list]:
    stands, pets = [], []
    joined = stopwatch.Lines()
    for line in lines or ():
        joined.add(line)
    watch = stopwatch.Stopwatch(
        lambda s: (joined.join(s), stands.append(s)), lambda p: (joined.join_pets(p), pets.append(p))
    )
    for sample in stream.samples:
        watch.feed(sample)
    watch.finish()
    return stands, pets


def stamp(at: float, text: str) -> str:
    """A probe.log line at `at` seconds of the stream (local time, ms)."""
    from datetime import datetime

    moment = datetime.fromtimestamp(WALL + at)
    return f'{moment:%Y-%m-%d %H:%M:%S},{moment.microsecond // 1000:03d} INFO {text}'


def hop_then_stand(stream: Stream, *, idle: int, chained: bool = False) -> None:
    """Walk, a Teleport (7 frames of cast, the jump on the 7th), `idle` frames neutral with the pets beside the
    character, then the Death Mark cast whose state shows 7 frames (0.28 s) in, with the pets going to the Herald in
    that frame, then a strike."""
    stream.sample(5)
    stream.mode, stream.skill = CASTING, stopwatch.TELEPORT
    stream.sample(6)
    stream.x += 15.0  # the jump; the pets come along
    stream.pets_at = None
    stream.sample(2)
    stream.mode = NEUTRAL
    stream.sample(idle)
    if chained:  # a strike's cast, the mark chained into it with no change of mode
        stream.mode, stream.skill = CASTING, stopwatch.ECHOING_STRIKE
        stream.sample(3)
    stream.mode, stream.skill = CASTING, stopwatch.DEATH_MARK
    stream.sample(7)
    stream.marked.add(HERALD)
    stream.pets_at = stream.foes_at[HERALD]
    stream.sample(2)
    stream.mode = NEUTRAL
    stream.sample(2)
    stream.mode, stream.skill = CASTING, stopwatch.ECHOING_STRIKE
    stream.sample(9)
    stream.mode = NEUTRAL
    stream.sample(20)


def test_the_ids_are_the_game_tables() -> None:
    excel = ROOT / 'pricing' / 'raw' / 'game-excel'
    if not (excel / 'states.txt').exists():
        pytest.skip('the game tables are not in this tree')
    states = {r.split('\t')[0]: int(r.split('\t')[1]) for r in (excel / 'states.txt').read_text().splitlines()[1:]}
    assert states['death_mark'] == stopwatch.MARK_STATE
    skills = {r.split('\t')[0]: r.split('\t')[1] for r in (excel / 'skills.txt').read_text().splitlines()[1:]}
    names = ('Teleport', 'Blade Warp', 'Death Mark', 'Echoing Strike')
    assert [int(skills[name]) for name in names] == [
        stopwatch.TELEPORT,
        stopwatch.BLADE_WARP,
        stopwatch.DEATH_MARK,
        stopwatch.ECHOING_STRIKE,
    ]
    monsters = [r.split('\t')[0] for r in (excel / 'monstats.txt').read_text().splitlines()[1:]]
    assert monsters[stopwatch.HIRELING] == 'act2hire'
    assert monsters[stopwatch.DEFILER] == 'warbighead'


def test_a_landing_is_timed_from_the_jump_to_the_mark_on_the_monster() -> None:
    stream = Stream()
    hop_then_stand(stream, idle=25)  # a second neutral
    stands, _ = run(stream)
    assert len(stands) == 1
    stand = stands[0]
    assert stand.hop == pytest.approx(-0.24)  # the cast began 6 frames before the jump
    assert stand.hop_skill == stopwatch.TELEPORT
    assert stand.stand == pytest.approx(0.08)  # the Teleport's cast ends 2 frames after the jump
    assert stand.first_cast == pytest.approx(0.08 + 25 * STEP)
    assert stand.first_skill == stopwatch.DEATH_MARK
    assert stand.mark_cast == pytest.approx(1.08)
    assert stand.mark_on == pytest.approx(1.08 + 0.28)
    assert stand.mark_unit == HERALD
    assert stand.strike == pytest.approx(1.08 + 0.28 + 0.16)
    assert stand.stood == pytest.approx(1.0)
    assert stand.neutral == pytest.approx(1.0)
    assert (stand.strike_near, stand.screen_near, stand.tier, stand.herald) == (2, 2, 5, True)
    assert 'merc 9.0' in stand.companions
    assert 'STOOD 1.00 s without a Death Mark' in stopwatch.say(stand)


def test_a_mark_chained_in_a_strike_is_a_cast_of_its_own() -> None:
    stream = Stream()
    hop_then_stand(stream, idle=5, chained=True)
    stand = run(stream)[0][0]
    assert stand.first_skill == stopwatch.ECHOING_STRIKE
    assert stand.mark_cast == pytest.approx(0.08 + 8 * STEP)  # 5 neutral, 3 of the strike
    assert [skill for _, skill in stand.casts][:2] == [stopwatch.ECHOING_STRIKE, stopwatch.DEATH_MARK]


def test_a_walk_is_no_landing_and_a_new_level_closes_the_stand() -> None:
    stream = Stream()
    for _ in range(30):
        stream.x += 0.3
        stream.sample()
    assert run(stream)[0] == []
    stream = Stream()
    hop_then_stand(stream, idle=3)
    level = stream.samples[-1]
    stream.samples.append(stopwatch.Sample(level.t + STEP, level.wall + STEP, 109, 500.0, 500.0, NEUTRAL, None))
    stands, _ = run(stream)
    assert len(stands) == 1
    assert stands[0].why_closed == 'level or gap'


def test_the_demons_stand_with_the_character_until_the_curse_sends_them() -> None:
    stream = Stream()
    hop_then_stand(stream, idle=25)
    key_at = 13 * STEP + 25 * STEP - 0.04  # the macro's key line, 40 ms before the cast shows
    landed_at = 11 * STEP + 0.005
    lines = [
        stamp(landed_at, 'Macro: teleport aimed at (115.0, 100.0), landed at (115.0, 100.0)'),
        stamp(key_at, 'Macro: Death Mark on d, player mode 1'),
        stamp(key_at + 0.06, "Macro: mark: designated the elite 3 (101): the tier 5 Herald pack's member"),
    ]
    stands, pets = run(stream, lines)
    assert len(pets) == 1
    stand = pets[0]
    assert stand.by == 'landing'
    assert stand.pets == ['Defiler', 'bound 189']  # not the mercenary
    assert stand.curse == pytest.approx(stand.length)  # they leave in the frame the curse shows
    assert stand.left_after_curse == pytest.approx(0.0)
    assert stand.length == pytest.approx(1.0 + 0.08 + 0.28)
    assert stand.keys == [pytest.approx(key_at - 11 * STEP, abs=0.002)]
    assert stand.mark_casts == [pytest.approx(1.08)]
    assert stand.heralded == 5
    parts = stands[0].parts()
    assert parts['notice'] == pytest.approx(0.005, abs=0.002)
    assert parts['flight'] == pytest.approx(0.04, abs=0.002)
    assert parts['curse'] == pytest.approx(0.28)
    assert 'PETS' in stopwatch.say_pets(stand)


def test_pets_in_a_scrum_at_the_character_are_fighting_not_standing() -> None:
    stream = Stream()
    stream.foes_at = {HERALD: (102.0, 100.0)}  # in melee with the pets beside the character
    stream.sample(40)
    assert run(stream)[1] == []
    stream = Stream()
    stream.foes_at = {}  # nothing to fight: no stand either
    stream.sample(40)
    assert run(stream)[1] == []


def test_a_marked_hostile_alive_while_the_demons_idle_is_counted() -> None:
    """A jump takes the demons off a marked target; the old mark does not send them back (20:18:00 on 2026-10-24)."""
    stream = Stream()
    stream.marked.add(MEMBER)
    hop_then_stand(stream, idle=50)
    pet = run(stream)[1][0]
    assert pet.marked_at_start == 1
    assert pet.marked_live == pytest.approx(pet.length - STEP, abs=STEP)


def test_the_take_lines_are_read_without_their_bulk(tmp_path: Path) -> None:
    take = tmp_path / '20261024T171736Z-108'
    take.mkdir()
    (take / 'manifest.json').write_text(json.dumps({'clock': {'monotonic': 10.0, 'wall': WALL + 10.0}}))
    words = bytearray(32)
    words[212 // 8] |= 1 << (212 % 8)
    frames, records = [], []
    for n, (x, mark) in enumerate([(100.0, False), (100.0, False), (115.0, True)], start=1):
        p = [7, 1, 108, x, 100.0, 390, 388, 2000, 2000, 700, 745]
        m = [[50, 3, 1, 110.0, 100.0, 128, 128, 16, stopwatch.NO_OWNER, 0], [60, DEFILER, 1, x, 100.0, 128, 230, 0,
             stopwatch.NO_OWNER, 1]]  # fmt: skip
        frames.append({'t': 10.0 + n * STEP, 'n': n, 'game': True, 'p': p, 'm': m, 'x': [[1, 2, 3, 4, 5, '00' * 48]]})
        states = bytes(words).hex() if mark else '00' * 32
        records.append({'t': 10.0 + n * STEP, 'n': n, 'u': [[50, 'ab' * 0x1C0, states, ''], [7, 'cd' * 8, '', '7701']]})
    (take / 'frames.jsonl').write_text(''.join(json.dumps(f, separators=(',', ':')) + '\n' for f in frames))
    (take / 'records.jsonl').write_text(''.join(json.dumps(r, separators=(',', ':')) + '\n' for r in records))
    (take / 'units.jsonl').write_text(json.dumps({'unit': 50, 'stats': {'367': 5}}) + '\n')
    samples = list(stopwatch.take_samples(take))
    assert [s.x for s in samples] == [100.0, 100.0, 115.0]
    assert samples[0].wall == pytest.approx(WALL + 10.04)
    assert samples[0].skill == 0x177  # 375, the u16 the skills.txt row begins with
    assert [s.foes[0].marked for s in samples] == [False, False, True]
    assert samples[0].foes[0].tier == 5
    assert samples[0].companions[0][1] == DEFILER  # an ally by its alignment, its owner unset
    live = stopwatch.LiveTake(take)
    assert [s.x for s in live.poll()] == [100.0, 100.0, 115.0]


def test_the_memory_sampler_reads_the_fields_in_one_batch() -> None:
    """A fake game: the character, one hostile with Death Mark on, the Defiler; each sample one `spans` call."""
    memory: dict[int, bytes] = {}

    def put(address: int, raw: bytes) -> None:
        memory[address] = raw

    def read(address: int, size: int) -> bytes:
        for start, raw in memory.items():
            if start <= address and address + size <= start + len(raw):
                return raw[address - start : address - start + size]
        raise OSError('unmapped')

    calls = []

    def spans(found: list[tuple[int, int]]) -> list:
        calls.append(len(found))
        out: list[bytes | None] = []
        for address, size in found:
            try:
                out.append(read(address, size))
            except OSError:
                out.append(None)
        return out

    def path(x: float, y: float) -> bytes:
        return struct.pack('<HHHH', int((x % 1) * 65536), int(x), int((y % 1) * 65536), int(y))

    player, foe, pet = 0x1000, 0x2000, 0x3000
    put(player + stopwatch.MODE_AT, struct.pack('<I', CASTING))
    put(0x10000, path(100.5, 200.0))  # the character's path
    put(0x11000 + stopwatch.SKILL_IN_USE, struct.pack('<Q', 0x12000))  # its skill list: the skill in use
    put(0x12000, struct.pack('<Q', 0x13000))
    put(0x13000, struct.pack('<H', stopwatch.DEATH_MARK))
    put(0x14000 + stopwatch.FULL_STATS, struct.pack('<QQ', 0x15000, 2))
    put(0x15000, struct.pack('<HHi', 0, 6, 1500 << 8) + struct.pack('<HHi', 0, 8, 600 << 8))
    put(foe + stopwatch.MODE_AT, struct.pack('<I', 1))
    put(0x20000, path(110.0, 200.0))
    put(0x21000 + stopwatch.STATE_FLAGS, struct.pack('<I', 1 << stopwatch.MARK_BIT))
    put(pet + stopwatch.MODE_AT, struct.pack('<I', 1))
    put(0x30000, path(100.6, 200.0))
    put(0x31000 + stopwatch.STATE_FLAGS, struct.pack('<I', 0))

    class Player:
        unit_id, area, x, y = 7, 108, 100.5, 200.0

    def walk():
        unit = {'address': player, 'path_pointer': 0x10000, 'stats_pointer': 0x14000,
                'record': bytes(stopwatch.SKILL_LIST) + struct.pack('<Q', 0x11000)}  # fmt: skip
        return (Player(), unit), []

    sampler = stopwatch.MemorySampler(read, spans, table=0, walk=walk, clock=lambda: 5.0)
    sampler.discover()
    sampler.units = {
        50: stopwatch.Tracked(50, 3, foe, 0x20000, 0x21000, tier=5, flags=8),
        60: stopwatch.Tracked(60, DEFILER, pet, 0x30000, 0x31000, ally=True),
    }
    sampler.found_at = 5.0
    sample = sampler.sample()
    assert sample is not None
    assert calls == [4 + 3 * 2]  # one batch of the few fields
    assert (sample.x, sample.y, sample.mode, sample.skill) == (100.5, 200.0, CASTING, stopwatch.DEATH_MARK)
    assert (sample.life, sample.mana, sample.area) == (1500, 600, 108)
    assert sample.foes == (stopwatch.Foe(50, 3, 1, 110.0, 200.0, 8, True, 5),)
    assert [c[1] for c in sample.companions] == [DEFILER]
    row = stopwatch.row_sample(json.loads(stopwatch.sample_row(sample)))
    assert row.foes == sample.foes
    assert row.skill == stopwatch.DEATH_MARK


def test_the_summary_puts_the_worst_first() -> None:
    stream = Stream()
    hop_then_stand(stream, idle=10)
    stream.marked.clear()
    stream.pets_at = (200.0, 200.0)
    stream.foes_at = {unit: (x + 15.0, y) for unit, (x, y) in stream.foes_at.items()}
    hop_then_stand(stream, idle=60)
    stands, pets = run(stream)
    rows = [stopwatch.stand_row(s) for s in stands] + [stopwatch.pet_row(p) for p in pets]
    text = stopwatch.summary(rows, worst=2)
    assert 'pet stands' in text
    assert 'stood without a Death Mark: n 2' in text
    worst = text.split('worst 2 pet stands (waited):\n')[1].splitlines()[0]
    assert f'{60 * STEP + 0.08 + 0.28:.2f} s' in worst
