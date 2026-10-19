"""Black Marsh, 22:43:59 to 22:44:31 on 2026-10-11: a quiet clear, attack mode alone among ordinary packs.

The take (fixtures/black-marsh-clear, frames 778 to 1559 of 20261011T194327Z-6, area 6) and the
service's log of the same seconds (probe.log beside it), seven minutes before the death in Tower
Cellar 5 (tower_cellar5.py) and under that evening's rules. After the last of a row of pickup keys
(22:43:59.949) the player pressed nothing for 33 s: the sweep went through the marsh by nine Blade
Warps, striking from each place, with two Sigils under elites and two Engorges under the held
strike. No drop was gone for (the log names gold piles only) and nothing was picked up.

The fixture has no paths.jsonl.gz (65 KB): the replay reads none.
"""

import json
import re
from datetime import datetime
from pathlib import Path

from inventory_tracking.game.records import Loot, Teleport
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.skills import NAMES
from tests.inventory_tracking.scenarios.battle.replay import Script

# The belt's item classes and the key of each skill are those of Tower Cellar 5, seven minutes later in
# the same session: the log names the same keys here ("Blade Warp on s", "Sigil: Lethargy on Button9",
# "Engorge on a") and the belt is as full ("belt short (0, 0)" at 22:44:00.057).
from tests.inventory_tracking.scenarios.battle.tower_cellar5 import BELT, KEYS


FIXTURE = Path(__file__).parent / 'fixtures' / 'black-marsh-clear'
# The fixture's first frame on the log's clock: the take began at 22:43:27.755 (the manifest's
# started_at; "Combat take … opened" at 22:43:27.755) and frame 778 is 32.030 s into it. Blade Warp's
# key went down 2.200 s into the fixture (events.jsonl) and the log says "Blade Warp on s" at
# 22:44:01.982 (2.197 s); over the 42 Blade Warps of the take the line is 20 ms before the key at the
# median, a tap's start.
OPENED = datetime(2026, 10, 11, 22, 43, 59, 785000)
# "Attack mode on" at 22:43:59.935, after a pickup key that found nothing: the replay starts the mode
# there. The player's last pickup key comes 14 ms later (`presses`, 22:43:59.949): it finds nothing
# either and hands its step to the sweep, which moves the mode by itself from then on.
BEGAN = 0.150
# "sweeping with 3 hostiles near and none in reach" at 22:44:31.107 is the last line replayed; the
# Blade Warp after the next (22:44:33.267) landed 28.9 off its aim: the player had taken over.
END = 31.6

# The skill slot table, from the take's manifest.
SLOTS = tuple(json.loads((FIXTURE / 'manifest.json').read_text())['slots'])

LINE = re.compile(r'^(\S+ \S+),(\d+) (\w+) (.*)$')


def seconds(stamp: str, milliseconds: str) -> float:
    at = datetime.strptime(stamp, '%Y-%m-%d %H:%M:%S').replace(microsecond=int(milliseconds) * 1000)
    return (at - OPENED).total_seconds()


def recorded() -> list[tuple[float, str]]:
    """The service's log of the stretch: (seconds into the fixture, the line without its stamp)."""
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
        if match and BEGAN <= at <= END:
            found.append((at, int(match[1])))
    return found


def busy() -> list[tuple[float, float]]:
    """The waits before each skill key: from the macro's line before it to the key itself. In them
    the macro looked for the character to be free and did not see it so (it would have pressed)."""
    lines = [(at, text) for at, text in recorded() if text.startswith('Macro') and BEGAN <= at <= END]
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
        if match and BEGAN <= at <= END:
            found.append((at - int(match[2]) / 1000, match[1]))
    return found


def loot(now: float, frame: dict) -> Loot:
    """The belt full and nothing on the ground worth a walk: "pickup: 0 drops (none), belt short (0, 0)"
    at 22:44:00.057. What fell in the 31 s after it is not in the log but for five gold piles, which
    the sweep did not go for; none is given here."""
    return Loot((), BELT, frame['p'][7], frame['p'][8], None)


def prepare(hunter) -> None:
    """What the hunt carried into the stretch, from the log: the step before it (the walk of
    22:43:59.456, ended by the pickup keys) counted as taken 0.69 s before the first cast ("first
    cast 0.69s after the step" at 22:44:00.593), and Hunter.take_step sets the sweep's last look for
    a better place to that moment: the next look is FOLLOW_CHECK on, not at once."""
    hunter.step_asked_at = hunter.sweep.looked = seconds('2026-10-11 22:44:00', '593') - 0.69


def key_names(world, skills=()):
    for skill in skills:
        if skill not in KEYS:
            raise Abort(f'{NAMES.get(skill, skill)} is not on a skill key')
    return dict(KEYS)


def script(**changes) -> Script:
    return Script(
        loot=loot,
        prepare=prepare,
        modes=modes(),
        busy=busy(),
        presses=[(BEGAN, 'hunt any'), *presses()],
        keys=KEYS,
        slots=SLOTS,
        # "69 charges" at the next hop by Teleport (22:45:06.974, after a weapon swap: the staff is in
        # the other set here). 69 is the most the evening's logs show: taken as its maximum.
        staff=Teleport(69, 69, False),
        **changes,
    )
