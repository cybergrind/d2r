"""Boss kills of one game launch, for farming runs (user, 2026-10-05).

A run is: make a game, kill the boss, leave. The probe's 'died' events (terror/probe.py) carry
the monster's txt id, so a boss kill is one of the ids below; its time is when the probe saw
the death start (the probe polls four times a second). Per boss the card line gives the kills,
the average time between consecutive kills (the whole loop, lobby included) and the time since
the last one, i.e. how long the current run has taken so far. A gap longer than OUTLIER times
the usual one (the lower median) is a stop, not a run, and is left out of the average (user,
2026-10-05). A boss not killed for IDLE_SECONDS, or IDLE_GAPS usual gaps if that is longer, is
not being farmed any more: its line is hidden until its next kill, the stats stay.

The stats belong to one launch of the game: the process identity (pid and start time,
native/process.py). Another identity starts from nothing. They are kept in a small file so a
restarted service continues the launch still running. A boss counts once per game (unit ids
start over in the next game), so the same unit dying twice in the probe's eyes is one kill.

Ids are d2data monstats.json `*hcIdx` (2026-10-05). Pindleskin and the Countess have no row of
their own: each is the only super unique of its class (superuniques.json), so they are the
units of that class first seen with the super unique type flag (monster data +0x1A & 0x02,
terror/tracker.py; the Countess's sightings in the probe logs carry 0x0a and her super unique
id 6 at +0x2A; Pindleskin's rule has counted his kills on the host since). Eldritch and Shenk
(2026-10-06) follow the same rule and are unconfirmed in-game.
"""

import json
import time
from itertools import pairwise
from pathlib import Path
from statistics import median_low

from inventory_tracking.common import LOG


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
# reanimatedhorde5, corruptrogue3; minion1 (superuniques 'Megaflow Rectifier', Eldritch the
# Rectifier by the Frigid Highlands waypoint) and overseer1 ('Siege Boss', Shenk the Overseer
# below it, at the top of the Bloody Foothills): each the only super unique of its class
# (2026-10-06). Their packs and the area's own Enslaved are the same classes without the flag.
SUPER_UNIQUES = {440: 'Pindleskin', 45: 'Countess', 453: 'Eldritch', 479: 'Shenk'}
TYPE_FLAGS, SUPER_UNIQUE_FLAG = 0x1A, 0x02  # monster data byte
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
