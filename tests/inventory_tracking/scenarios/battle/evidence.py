"""The macro's log read as actions, the same way for the service's log of a battle and for a replay's.

An `Action` is what the macro did or decided, without the numbers that only describe it: a strike's
line is the unit it goes through and its focal point, a move is its kind and its place. `compare`
lines two lists up and says where they part.
"""

import difflib
import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    at: float  # seconds into the take
    kind: str
    what: str = ''  # the unit, the skill, the drop: what must be the same for two actions to be the same
    place: tuple[float, float] | None = None  # the focal point, the place gone to: compared within a tolerance
    text: str = ''

    @property
    def key(self) -> tuple[str, str]:
        return self.kind, self.what


PAIR = r'\((-?[\d.]+), (-?[\d.]+)\)'
# (kind, pattern, group of `what`, groups of the place). The first that matches names the line.
RULES: tuple[tuple[str, str, int | None, tuple[int, int] | None], ...] = (
    ('press', r'request ([a-z ]+), \d+ ms old', 1, None),
    ('mode on', r'Attack mode on$', None, None),
    ('mode paused', r'Attack mode paused$', None, None),
    ('mode off', r'Attack mode off$', None, None),
    ('strike', r'Echoing Strike \([^)]*\) at the (?:monster|elite|boss) \d+ \((\d+)\)', 1, None),
    ('line', rf'line through the (?:monster|elite|boss) \d+ \((\d+)\), \d+/\d+, [\d.]+ away, focal {PAIR}', 1, (2, 3)),
    ('sweep', rf'sweeping .*: a place at {PAIR}, a (jump by Blade Warp|walk|jump by Teleport|hop)', 3, (1, 2)),
    (
        'step',
        rf'step asked in the fight .*: a place at {PAIR}, a (jump by Blade Warp|walk|jump by Teleport|hop)',
        3,
        (1, 2),
    ),
    ('no step', r'step asked in the fight .*: no better place', None, None),
    ('stand', r'Standing well', None, None),
    ('sweep takes', r'step asked with \d+ hostiles near.*: the sweep takes it', None, None),
    ('walk', r'Walking \d+ toward a better place', None, None),
    (
        'skill',
        r'(Blade Warp|Sigil: Lethargy|Engorge|Death Mark|Teleport|Hex: Purge|Swap Weapons) on (\S+), player',
        1,
        None,
    ),
    ('landed', rf'Blade Warp aimed at {PAIR}', None, (1, 2)),
    ('engorge', r'Engorge on the corpse (\d+)', None, None),
    ('no engorge', r'no Engorge at', None, None),
    ('key wait', r'(.+) still on the right button', 1, None),
    ('fight end', r'fight \([^)]*\): \d+ casts seen in [\d.]+s, \d+ down; (.+)$', 1, None),
    ('fight stopped', r'the fight stopped \((.+)\), \d+ in a row', 1, None),
    ('idle', r'idle: \d+ hostiles, none in reach', None, None),
    ('waiting', r'waiting \((.+)\)', 1, None),
    (
        'pickup look',
        r'pickup: \d+ drops \([a-z, ]*\), belt short \(\d+, \d+\), life \d+/\d+; (nothing to pick up|.+ at)',
        1,
        None,
    ),
    ('not picked', r'Not picked up: (.+)$', 1, None),
    ('pickup asked', r'pickup asked in the fight .*: (.+) first', 1, None),
    ('sweep stops', r'the sweep stops for (.+), \d+ away', 1, None),
    ('sweep leaves', r'the sweep leaves (.+) for later', 1, None),
    ('drink', r'Drinking \((\d)\)', 1, None),
    ('picking', r'Picking up (.+), \d+ away', 1, None),
    ('click missed', r'(.+) at \([\d., ]+\) still on the ground after the click \((-?\d+, -?\d+)\)', 2, None),
    ('every aim', r'clicking every aim', None, None),
    ('picked', r'picked up (.+?) [\d.]+s after', 1, None),
    ('stopped', r'^Macro stopped: (.+)$', 1, None),
    ('dropped', r'(\w+) dropped: it waited', 1, None),
    ('dead', r'the character is dead', None, None),
)
QUIET = (
    'Last minute:', 'first cast', 'aims for', ': 1 down in', 'down in', 'unit table census', 'Combat take',
    'slow press', '(replay)', 'leg time:',  # a move's measure (macros/travel.py), not an action
    'mark: no ',  # why a Death Mark was not cast (builds/warlock/mark.py, 2026-10-14): a reason, not an action
    'firing stand jump source',  # which jump a firing stand took (macros/hunt.py, b3757e4): a reason
)  # fmt: skip


def read(lines: list[tuple[float, str]]) -> list[Action]:
    """The actions in `lines` ((seconds, text)); a line no rule knows is kept as 'other', so nothing
    the macro said goes unseen."""
    found = []
    for at, text in lines:
        body = text.removeprefix('Macro: ')
        if any(mark in text for mark in QUIET):
            continue
        for kind, pattern, what, place in RULES:
            match = re.search(pattern, text if pattern.startswith('^') else body)
            if match:
                where = (float(match[place[0]]), float(match[place[1]])) if place else None
                found.append(Action(at, kind, match[what] if what else '', where, body))
                break
        else:
            found.append(Action(at, 'other', body, None, body))
    return found


REORDER = 0.1


@dataclass
class Compared:
    same: list[tuple[Action, Action]]  # (recorded, replayed), in order
    missing: list[Action]  # recorded, not replayed
    extra: list[Action]  # replayed, not recorded

    @property
    def share(self) -> float:
        total = len(self.same) + len(self.missing) + len(self.extra)
        return len(self.same) / total if total else 1.0

    def first_parting(self) -> float | None:
        apart = [action.at for action in (*self.missing, *self.extra)]
        return min(apart) if apart else None

    def drift(self) -> float:
        """The largest gap in seconds between a recorded action and its replay."""
        return max((abs(a.at - b.at) for a, b in self.same), default=0.0)

    def off(self) -> float:
        """The largest distance in units between a recorded place and its replay's."""
        return max((math.dist(a.place, b.place) for a, b in self.same if a.place and b.place), default=0.0)

    def table(self) -> str:
        rows = [(a.at, f'  = +{a.at:6.2f} | +{b.at:6.2f}  {a.kind}: {a.what or a.text[:60]}') for a, b in self.same]
        rows += [(a.at, f'  - +{a.at:6.2f} |          {a.kind}: {a.what}   [{a.text[:90]}]') for a in self.missing]
        rows += [(b.at, f'  +         | +{b.at:6.2f}  {b.kind}: {b.what}   [{b.text[:90]}]') for b in self.extra]
        return '\n'.join(text for _, text in sorted(rows, key=lambda row: row[0]))


def compare(recorded: list[Action], replayed: list[Action]) -> Compared:
    """The two lists lined up in order by kind and what (the longest common run of actions)."""
    matcher = difflib.SequenceMatcher(a=[a.key for a in recorded], b=[b.key for b in replayed], autojunk=False)
    same, missing, extra = [], [], []
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag == 'equal':
            same += list(zip(recorded[a0:a1], replayed[b0:b1], strict=True))
        else:
            missing += recorded[a0:a1]
            extra += replayed[b0:b1]
    # The same action on both sides within REORDER seconds is the same action in another order: two
    # lines of one millisecond (a key and the strike it meets) have no order worth a difference.
    for then in list(missing):
        twin = next((now for now in extra if now.key == then.key and abs(now.at - then.at) <= REORDER), None)
        if twin is not None:
            missing.remove(then)
            extra.remove(twin)
            same.append((then, twin))
    same.sort(key=lambda pair: pair[0].at)
    return Compared(same, missing, extra)
