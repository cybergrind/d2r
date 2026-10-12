"""The Moo Moo Farm, 02:18:50 to 02:19:09 on 2026-10-12: attack mode alone in the herd.

The take (fixtures/cows-stand, frames 6174 to 6616 of 20261011T231408Z-39, area 39) and the service's
log of the same seconds (probe.log beside it). Between two pickup keys (02:18:50.864 and 02:19:08.831)
the player pressed nothing: the sweep jumped in by Blade Warp, struck, strode on by a second Blade Warp
and a walk, fought 5.6 s in the herd and stepped three more times by Blade Warp, 33 cows down by the
log's own count. No drop was gone for and no key but Blade Warp's went under the strike.

The fixture has no paths.jsonl.gz: a trim keeps every path record before its first frame, 592 KB of the
herd's 281 s here, and the replay reads none.
"""

import json
import re
from datetime import datetime
from pathlib import Path

from inventory_tracking.builds.warlock.buffs import ENGORGE_HURT_SECONDS, ENGORGE_RETRY
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.skills import NAMES
from inventory_tracking.macros.world import Loot, Teleport
from tests.inventory_tracking.scenarios.battle.replay import Script

# The belt's item classes and the key of each skill are the character's of four hours before (Tower
# Cellar 5): the log of this game names the same keys where it names one ("Blade Warp on s", "Engorge
# on a", "Death Mark on d", "Hex: Purge on g", "Psychic Ward on r", "Consume on 6", "Teleport on t",
# "Sigil: Lethargy on Button9") and the belt is as full ("belt short (0, 0)" at 02:18:50.903).
from tests.inventory_tracking.scenarios.battle.tower_cellar5 import BELT, KEYS


FIXTURE = Path(__file__).parent / 'fixtures' / 'cows-stand'
# The fixture's first frame on the log's clock: the take began at 02:14:08.814 (the manifest's
# started_at; "Combat take … opened" at 02:14:08.815) and frame 6174 is 281.524 s into it. Blade
# Warp's key went down 0.784 s into the fixture (events.jsonl) and the log says "Blade Warp on s" at
# 02:18:51.105, a tap's start before it, as in the 66 Blade Warps of the take (13 ms at the median).
OPENED = datetime(2026, 10, 12, 2, 18, 50, 338000)
# "Attack mode on" at 02:18:50.452, when the pickup before the stretch had taken its Ring: the replay
# starts the mode there. The pickup key of 02:18:50.864 comes next (`presses`): it finds nothing to
# take and hands its step to the sweep, which is what makes the mode move by itself afterwards.
BEGAN = 0.114
END = 18.4  # the next pickup key is at 18.49 s (02:19:08.831)

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
    """The character's mode at each skill key, as the macro read it ("Blade Warp on s, player mode 1")."""
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
    """The belt full and nothing on the ground worth a walk. The log has two super healing potions
    near ("2 drops (healing)" at 02:18:50.903) and not their places; with the belt full the pickup
    left them ("the belt has no place for a super healing potion") and the sweep said nothing of a
    drop in the stretch: they are left out."""
    return Loot((), BELT, frame['p'][7], frame['p'][8], None)


def prepare(hunter) -> None:
    """What the hunt carried into the stretch, from the log before it: the last look for a corpse at
    02:18:42.926 ("no Engorge at (25313.5, 6013.5)", the second of two: Rotation.engorge then sets
    the next look ENGORGE_RETRY on)."""
    hunter.rotation.engorged_at = seconds('2026-10-12 02:18:42', '926') - ENGORGE_HURT_SECONDS + ENGORGE_RETRY


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
        # "67 charges" at 02:16:11.277 with one hop to make, "66 charges" at 02:19:30.443; the staff
        # is in the other set (the strike is in hand). 69 is the most the night's logs show
        # (02:14:40.140): taken as its maximum.
        staff=Teleport(66, 69, False),
        **changes,
    )
