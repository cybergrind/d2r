"""Boss kills of one game launch, for farming runs (user, 2026-10-05).

A kill is a probe 'died' event (terror/probe.py) of a boss txt id. Per boss the card line gives
the kills, the average gap between kills (whole loop, lobby included) and the time since the last.
A gap over OUTLIER times the lower median is a stop and left out of the average (user, 2026-10-05);
a boss idle for IDLE_SECONDS (or IDLE_GAPS usual gaps) is hidden until its next kill.

Stats belong to one game launch (pid + start time, native/process.py), saved to a file so a
restarted service continues it. A boss unit counts once per game.

Ids: d2data monstats.json `*hcIdx`. A super unique without its own row (SUPER_UNIQUES) is the unit
of its class seen with the super unique type flag (monster data +0x1A & 0x02); Eldritch and Shenk
are unconfirmed in-game (2026-10-06).
"""

import json
import time
from itertools import pairwise
from pathlib import Path
from statistics import median_low

from inventory_tracking.common import LOG
from inventory_tracking.game.layout import SUPER_FLAG as SUPER_UNIQUE_FLAG, TYPE_FLAGS


# time.monotonic() of each boss's last kill (macros/loop.py DROPS_AFTER_KILL waits from it)
KILLED_AT: dict[str, float] = {}


BOSSES = {
    156: 'Andariel',
    211: 'Duriel',
    242: 'Mephisto',
    243: 'Diablo',
    544: 'Baal',  # baalcrab, the Worldstone Chamber fight
    250: 'Summoner',
    256: 'Izual',
    526: 'Nihlathak',
}
# reanimatedhorde5, corruptrogue3, minion1, overseer1: each the only super unique of its class
# (superuniques.json); their packs are the same classes without the flag.
SUPER_UNIQUES = {440: 'Pindleskin', 45: 'Countess', 453: 'Eldritch', 479: 'Shenk'}
OUTLIER = 2.5  # times the median gap: longer is a break
IDLE_SECONDS, IDLE_GAPS = 600, 3  # without a kill for this long: no longer farmed, not shown
MAX_KILLS = 500  # kill times kept per boss


def duration(seconds: float) -> str:
    seconds = max(0, round(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes = f'{rest // 60:02d}' if hours else f'{rest // 60}'
    return (f'{hours}:' if hours else '') + f'{minutes}:{rest % 60:02d}'


def usual_gap(times: list[float]) -> float:
    """Mean seconds between consecutive kills, breaks left out; `times` holds two kills or more."""
    gaps = [later - earlier for earlier, later in pairwise(times)]
    limit = OUTLIER * median_low(gaps)
    runs = [gap for gap in gaps if gap <= limit]
    return sum(runs) / len(runs)


class BossTracker:
    def __init__(self, path: Path | None = None, *, clock=time.time, shown=3):
        self.path, self.clock, self.shown = path, clock, shown
        self.game = None  # identity of the game process the kills belong to
        self.kills: dict[str, list[float]] = {}  # boss -> kill times (clock seconds), oldest first
        self.counted: set[int] = set()  # boss unit ids counted in the current game
        self.named: dict[int, str] = {}  # unit id -> super unique boss seen in the current game

    def load(self, game) -> dict[str, list[float]]:
        if self.path is None:
            return {}
        try:
            saved = json.loads(self.path.read_text(encoding='utf-8'))
            if saved['game'] != game:
                return {}
            return {str(name): [float(at) for at in times] for name, times in saved['kills'].items()}
        except OSError, ValueError, KeyError, TypeError, AttributeError:
            return {}

    def save(self):
        if self.path is None:
            return
        try:
            self.path.write_text(json.dumps({'game': self.game, 'kills': self.kills}), encoding='utf-8')
        except OSError as exc:
            LOG.warning('Boss kills not saved to %s: %s', self.path, exc)

    def apply(self, game, events):
        """`game`: the identity of the game process the probe's `events` come from."""
        if game != self.game:
            self.game, self.kills, self.counted, self.named = game, self.load(game), set(), {}
        changed = False
        for event in events:
            if event['event'] == 'left_game':
                self.counted.clear()
                self.named.clear()
            elif event['event'] == 'seen':
                name = SUPER_UNIQUES.get(event.get('txt_id'))
                data = event.get('data_hex') or ''
                flags = data[2 * TYPE_FLAGS : 2 * TYPE_FLAGS + 2]
                if name and len(flags) == 2 and int(flags, 16) & SUPER_UNIQUE_FLAG:
                    self.named[event['unit_id']] = name
            elif event['event'] == 'died':
                name = BOSSES.get(event.get('txt_id')) or self.named.get(event['unit_id'])
                if name is None or event['unit_id'] in self.counted:
                    continue
                self.counted.add(event['unit_id'])
                self.kills[name] = [*self.kills.get(name, []), self.clock()][-MAX_KILLS:]
                changed = True
                LOG.info('Boss kill: %s, %s this launch', name, len(self.kills[name]))
                KILLED_AT[name] = time.monotonic()
        if changed:
            self.save()

    def lines(self) -> list[str]:
        """A line per boss being farmed this launch, the most recent kill first."""
        now, lines = self.clock(), []
        for name, times in sorted(self.kills.items(), key=lambda item: -item[1][-1])[: self.shown]:
            usual = usual_gap(times) if len(times) > 1 else 0
            if now - times[-1] > max(IDLE_SECONDS, IDLE_GAPS * usual):
                continue
            parts = [name, f'{len(times)} kill' + ('s' if len(times) > 1 else '')]
            if len(times) > 1:
                parts.append(f'avg {duration(usual)}')
            parts.append(f'last {duration(now - times[-1])} ago')
            lines.append(' · '.join(parts))
        return lines
