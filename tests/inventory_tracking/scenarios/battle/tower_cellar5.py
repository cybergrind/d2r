"""Tower Cellar 5, 22:50:37 to 22:51:00 on 2026-10-11: the fight the character died in.

The take (fixtures/tower-cellar5-herald, trimmed from 20261011T195037Z-25) and the service's log of
the same seconds (probe.log beside it). A Herald pack (the elite Blood Clan 2960229440 and nine
minions) came 13 s in; 18.2 s in the sweep stopped the fight for a potion; the character died at
23.1 s with the Herald at 82 of 128 (macros/plan.md, 2026-10-12 05:00).
"""

import re
from datetime import datetime
from pathlib import Path

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.skills import NAMES
from inventory_tracking.macros.world import HEALING, Drop, Loot, Teleport
from tests.inventory_tracking.scenarios.battle.replay import Script


FIXTURE = Path(__file__).parent / 'fixtures' / 'tower-cellar5-herald'
# The take's first frame on the log's clock: Blade Warp's key went down 1.573 s into the take
# (events.jsonl) and the log says "Blade Warp on s" at 22:50:39.129, a tap's start before it.
OPENED = datetime(2026, 10, 11, 22, 50, 37, 570000)
DEATH = 23.1  # seconds into the take: the character's mode is 0

# The skill slot table as the logs of that evening print it ("slots 379,390,375,…").
SLOTS = (379, 390, 375, 384, 389, 220, 393, 377, 226, 382, 387, 54, 381, 221, None, None)
# The key of each skill, as the log names them ("Blade Warp on s"); Echoing Strike is on the right
# mouse button and on no key.
KEYS = {379: 'a', 390: 's', 375: 'd', 389: 'g', 393: 'Button9', 377: 'q', 387: 'r', 54: 't', 381: '6'}
# The belt: full ("belt short (0, 0)"), healing potions in the third column ("Drinking (3)"); the
# first two taken as full rejuvenations, the fourth as healing (not in the log).
BELT = (531, 531, 606, 606) * 4
POTION = Drop(
    2637202393, 12582.0, 11109.0, 'a super healing potion', HEALING
)  # "(unit 2637202393) at (12582.0, 11109.0)"
# "2 drops (healing)", "1 wanted and 1 other drops": a second healing potion, whose place the log does
# not give. Assumed beside the first.
OTHER = Drop(2637202394, 12584.0, 11111.0, 'a super healing potion', HEALING)
# The log's first sight of the two: "2 drops" at 22:50:48.07, none at 22:50:43.16. Assumed to have
# fallen with the kills of the cast 6.7 s in.
DROPPED = 7.5
# The walk of 2.93 s ("Walking 23 toward a better place", clicked at 3.35 s) took the character 1.99
# units, from (12574.50, 11127.50) to (12576.49, 11127.50) in the take's frames, where a step counts
# as made from 2.0 units on (teleport.MOVED). In the game it counted, and late: no "No step" follows
# it, and the fight began at about 3.97 s ("1 casts seen in 0.2s" at 4.17 s), half a second after
# the character had stopped and before the wait could run out (4.09 s). The standing character's
# place flickers by a hundredth in the frames (12576.50 at 4.24 s, 12576.49 around it): one look
# between two frames is taken to have shown 12576.50.
PLACES = [(3.93, 3.97, 12576.50, 11127.50)]

LINE = re.compile(r'^(\S+ \S+),(\d+) (\w+) (.*)$')


def seconds(stamp: str, milliseconds: str) -> float:
    at = datetime.strptime(stamp, '%Y-%m-%d %H:%M:%S').replace(microsecond=int(milliseconds) * 1000)
    return (at - OPENED).total_seconds()


def recorded() -> list[tuple[float, str]]:
    """The service's log of the fight: (seconds into the take, the line without its stamp)."""
    found = []
    for line in (FIXTURE / 'probe.log').read_text().splitlines():
        match = LINE.match(line)
        if match:
            found.append((seconds(match[1], match[2]), match[4]))
    return found


def modes() -> list[tuple[float, int]]:
    """The character's mode at each skill key, as the macro read it ("Engorge on a, player mode 1")."""
    found = []
    for at, text in recorded():
        match = re.search(r' on \S+, player mode (\d+)$', text)
        if match:
            found.append((at, int(match[1])))
    return found


def busy() -> list[tuple[float, float]]:
    """The waits before each skill key: from the macro's line before it to the key itself. In them
    the macro looked for the character to be free and did not see it so (it would have pressed)."""
    lines = [(at, text) for at, text in recorded() if text.startswith('Macro')]
    found = []
    for index, (at, text) in enumerate(lines):
        if re.search(r' on \S+, player mode \d+$', text) and index >= 2:
            found.append((lines[index - 2][0], at - 0.045))  # the line before is the skill's own name
    return found


def presses() -> list[tuple[float, str]]:
    """The player's keys, from the log's "Macro: request <routine>, N ms old" lines."""
    found = []
    for at, text in recorded():
        match = re.match(r'Macro: request ([a-z ]+), (\d+) ms old', text)
        if match:
            found.append((at - int(match[2]) / 1000, match[1]))
    return found


class Carried:
    """The belt as the keys change it: a potion drunk leaves its column's top cell free."""

    def __init__(self) -> None:
        self.belt: list[int | None] = list(BELT)

    def loot(self, now: float, frame: dict) -> Loot:
        life, most = frame['p'][7], frame['p'][8]
        drops = (POTION, OTHER) if now >= DROPPED else ()
        return Loot(drops, tuple(self.belt), life, most, None)

    def on_input(self, now: float, event: tuple) -> None:
        if event[0] == 'key' and event[1] in '1234':
            column = int(event[1]) - 1
            cells = [cell for cell in range(column, len(self.belt), 4) if self.belt[cell] is not None]
            if cells:
                self.belt[cells[-1]] = None


def prepare(hunter) -> None:
    """What the hunt carried into the level, from the log before the take: the last Engorge at
    22:50:23.633 ("Engorge on the corpse 1615699704"), 13.94 s before the take's first frame."""
    hunter.rotation.engorged_at = seconds('2026-10-11 22:50:23', '633')


def key_names(world, skills=()):
    for skill in skills:
        if skill not in KEYS:
            raise Abort(f'{NAMES.get(skill, skill)} is not on a skill key')
    return dict(KEYS)


def script(**changes) -> Script:
    carried = Carried()
    return Script(
        loot=carried.loot,
        on_input=carried.on_input,
        prepare=prepare,
        modes=modes(),
        busy=busy(),
        places=PLACES,
        # The teleport step into the level ended at 22:50:37.587 and attack mode followed it at
        # 22:50:38.089 (TRAVEL_QUIET was 0.5 s): the replay starts the mode there.
        presses=[(0.52, 'hunt any'), *presses()],
        keys=KEYS,
        slots=SLOTS,
        staff=Teleport(1, 20, False),  # "1 charges kept"
        **changes,
    )
