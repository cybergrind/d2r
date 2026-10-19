"""The moments of a recorded battle worth cutting into an arena scene, found by rule (framework-plan.md,
Task 1.4): a death, a burst of damage, a run of potions, a long fight. Each moment places its frame LEAD
seconds before its event, so the scene starts before the trouble."""

from bisect import bisect_right
from dataclasses import dataclass
from math import hypot

from inventory_tracking.macros.routines import DEAD
from inventory_tracking.takes.takes import PlayerRow, Take, monsters_of, player_of


BURST_SHARE = 0.3  # of the most life (danger-plan.md R4: terror/bursts.py SHARE, in git history)
BURST_WINDOW = 1.0  # seconds (bursts.py WINDOW)
POTIONS = 3  # belt keys ...
POTIONS_WINDOW = 10.0  # ... within this many seconds
LONG_REACH = 30.0  # world units from the character
LONG_SECONDS = 20.0  # hostiles within LONG_REACH this long without a gap
LONG_GAP = 1.0  # seconds: a longer gap between two frames of a fight ends it
LEAD = 3.0  # seconds before the event at which the moment is placed: the scene starts before the trouble
APART = 5.0  # seconds: two moments of one kind nearer than this are one (the first)


@dataclass(frozen=True)
class Moment:
    frame: int  # index into take.frames
    # 'death' | 'burst' | 'potions' | 'long'; from others: 'stuck' (stuck.py), 'burst<percent>' (build_scenes.py)
    kind: str
    at: float  # seconds from the take's first frame, of the event itself (not of the lead)
    note: str  # one line a person can read, with the numbers that made it a moment


def moments(take: Take, *, belt_keys: frozenset[int] = frozenset(), burst_share: float = BURST_SHARE) -> list[Moment]:
    """The moments of a take, sorted by `at` then kind; `belt_keys` are the potion keys' codes, `burst_share`
    the share of the most life that makes a burst (a lighter one widens the choice of scenes)."""
    frames = take.frames
    if not frames:
        return []
    start = frames[0]['t']
    rel = [frame['t'] - start for frame in frames]
    rows = [(index, player) for index, frame in enumerate(frames) if (player := player_of(frame)) is not None]
    found: list[Moment] = []
    death = _death(rows, rel)
    if death is not None:
        found.append(death)
    found += _bursts(rows, rel, burst_share)
    found += _potions(take, start, rel, belt_keys)
    found += _long(frames, rows, rel)
    return _merged(found)


def _place(rel: list[float], at: float) -> int:
    """The last frame whose time is at most `at - LEAD`, clamped to the first frame."""
    return max(bisect_right(rel, at - LEAD) - 1, 0)


def _death(rows: list[tuple[int, PlayerRow]], rel: list[float]) -> Moment | None:
    """The first frame in which the character is dead (life 0 of a known most life, or a dead mode)."""
    # Seen alive in this take: one that opens on the corpse (the walk back, 20261011T195359Z-25) holds no death.
    alive = False
    for index, player in rows:
        if player.mode not in DEAD and (player.life or player.life is None):
            alive = True
            continue
        # A frame whose vitals were not read shows life 0 of 0 (13 of the last 120 takes on 2026-10-12): not a death.
        if alive and ((player.life == 0 and player.max_life) or player.mode in DEAD):
            at = rel[index]
            return Moment(_place(rel, at), 'death', at, f'dead at {at:.1f} s')
    return None


def _bursts(rows: list[tuple[int, PlayerRow]], rel: list[float], share: float = BURST_SHARE) -> list[Moment]:
    """Frames where the life fell by `share` of the max life since the highest life in the window."""
    known = [(i, p.life, p.max_life) for i, p in rows if p.life is not None and p.max_life]
    found = []
    for pos, (index, life, max_life) in enumerate(known):
        peak = None
        for back in range(pos - 1, -1, -1):
            earlier, before, _max = known[back]
            if rel[index] - rel[earlier] > BURST_WINDOW:
                break
            if peak is None or before > peak[1]:
                peak = (earlier, before)
        if peak is None:
            continue
        lost = peak[1] - life
        if lost > 0 and lost >= share * max_life:
            at = rel[index]
            within = at - rel[peak[0]]
            note = f'life {peak[1]} -> {life} of {max_life} within {within:.2f} s'
            found.append(Moment(_place(rel, at), 'burst', at, note))
    return found


def _potions(take: Take, start: float, rel: list[float], belt_keys: frozenset[int]) -> list[Moment]:
    """Runs of POTIONS belt key-downs within POTIONS_WINDOW seconds, placed at the run's first key."""
    if not belt_keys:
        return []
    presses = sorted(
        event['t'] - start
        for event in take.events
        if event['event'] == 'keys'
        for code in event.get('down') or ()
        if code in belt_keys
    )
    found = []
    for pos, first in enumerate(presses):
        window = bisect_right(presses, first + POTIONS_WINDOW, pos)
        count = window - pos
        if count >= POTIONS:
            span = presses[window - 1] - first
            found.append(Moment(_place(rel, first), 'potions', first, f'{count} potions within {span:.1f} s'))
    return found


def _long(frames: list[dict], rows: list[tuple[int, PlayerRow]], rel: list[float]) -> list[Moment]:
    """Stretches of frames each with a hostile within LONG_REACH, at least LONG_SECONDS long; no lead."""
    found: list[Moment] = []
    run: list[int] | None = None  # the first and last frame of the stretch being read
    for index, player in rows:
        near = any(
            monster.hostile and hypot(monster.x - player.x, monster.y - player.y) <= LONG_REACH
            for monster in monsters_of(frames[index])
        )
        if run is not None and (not near or rel[index] - rel[run[1]] > LONG_GAP):
            found += _stretch(run, rel)
            run = None
        if near:
            run = [index, index] if run is None else [run[0], index]
    if run is not None:
        found += _stretch(run, rel)
    return found


def _stretch(run: list[int], rel: list[float]) -> list[Moment]:
    seconds = rel[run[1]] - rel[run[0]]
    if seconds < LONG_SECONDS:
        return []
    return [Moment(run[0], 'long', rel[run[0]], f'hostiles within {LONG_REACH:.0f} for {seconds:.1f} s')]


def _merged(found: list[Moment]) -> list[Moment]:
    """Sorted by `at` then kind, a moment within APART of the kept one of its kind is dropped."""
    kept: list[Moment] = []
    last: dict[str, float] = {}
    for moment in sorted(found, key=lambda m: (m.at, m.kind)):
        if moment.kind in last and moment.at - last[moment.kind] < APART:
            continue
        last[moment.kind] = moment.at
        kept.append(moment)
    return kept
