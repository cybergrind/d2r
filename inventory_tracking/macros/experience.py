"""The experience the KP_6 loop's terror zone kinds gain: TZ leveling's measure (the player, 2026-10-19 21:37: "we
should log experience in tz leveling"). Pure bookkeeping: loop.py `Loop.leg` hands it the character's stats at each
leg's look (`look`: a level's gain when the level is left) and at Save and Exit (`game_over`: the game's gain and the
rate since the loop turned on); it returns the log lines, never reads the game.

`Macro: experience: game N: +X (level L, Y to the next), Z an hour over H games` and
`Macro: experience: <level>: +X in Ts (level L)` (d2-loop-watch tools/logwords.py EXPERIENCE_GAME, EXPERIENCE_LEVEL).
"""

from collections.abc import Mapping
from dataclasses import dataclass

from inventory_tracking.levels.presets import display_name
from inventory_tracking.native.layout import TOWN_IDS


# itemstatcost.txt *ID (pricing/raw/game-excel/itemstatcost.txt, 2026-10-19): `level` 12, `experience` 13, both
# ValShift 0 in the unit's full stat list; experience is 32 bits, read as signed (native/units.py `read_stats`)
LEVEL_STAT = 12
EXPERIENCE_STAT = 13
# experience.txt (third-parties/d2data json/experience.json fc46999, with the Warlock column; every class's the same):
# row L is the total experience at which level L becomes L + 1; row 99 is the cap
_TABLE = """
0 500 1500 3750 7875 14175 22680 32886 44396 57715 72144 90180 112725 140906 176132 220165 275207 344008 430010
537513 671891 839864 1049830 1312287 1640359 2050449 2563061 3203826 3902260 4663553 5493363 6397855 7383752
8458379 9629723 10906488 12298162 13815086 15468534 17270791 19235252 21376515 23710491 26254525 29027522
32050088 35344686 38935798 42850109 47116709 51767302 56836449 62361819 68384473 74949165 82104680 89904191
98405658 107672256 117772849 128782495 140783010 153863570 168121381 183662396 200602101 219066380 239192444
261129853 285041630 311105466 339515048 370481492 404234916 441026148 481128591 524840254 572485967 624419793
681027665 742730244 809986056 883294891 963201521 1050299747 1145236814 1248718217 1361512946 1484459201
1618470619 1764543065 1923762030 2097310703 2286478756 2492671933 2717422497 2962400612 3229426756 3520485254
3837739017
"""
NEXT_LEVEL_AT = tuple(int(value) for value in _TABLE.split())
MAX_LEVEL = 99
RATE_HOURS = 1 / 60  # a rate over less than a minute says '?': a game takes minutes


@dataclass(frozen=True)
class Reading:
    """The character's experience and level at one look."""

    experience: int
    level: int

    @property
    def to_next(self) -> int | None:
        """Experience still wanted for the next level; None at the cap or past the table."""
        if not 0 < self.level < MAX_LEVEL or self.level >= len(NEXT_LEVEL_AT):
            return None
        return max(0, NEXT_LEVEL_AT[self.level] - self.experience)


def reading(stats: Mapping[int, int] | None) -> Reading | None:
    """The reading in a unit's {stat id: raw} list; None without both stats."""
    if not stats or EXPERIENCE_STAT not in stats or not stats.get(LEVEL_STAT):
        return None
    return Reading(stats[EXPERIENCE_STAT] & 0xFFFFFFFF, stats[LEVEL_STAT])  # unsigned: past 2**31 from level 92


def gained(amount: int) -> str:
    return f'{amount:+,}'


@dataclass
class Ledger:
    """The experience since the loop turned on (`Loop.start` makes a new one), per game and per level."""

    first: Reading | None = None  # the first reading since the loop turned on, and its clock
    since: float = 0.0
    game: str | None = None  # the game looked at last, its first reading
    game_start: Reading | None = None
    area: int | None = None  # the level looked at last, its first reading and clock
    level_start: Reading | None = None
    level_since: float = 0.0
    games: int = 0  # games ended (`game_over`) with a reading

    def look(self, game: str, area: int | None, now: Reading | None, clock: float) -> list[str]:
        """A leg's look in `game` on level `area`: the last level's line when it was left. Nothing unread."""
        if now is None:
            return []
        if self.first is None:
            self.first, self.since = now, clock
        if game != self.game:
            self.game, self.game_start, self.area, self.level_start = game, now, None, None
        lines = []
        if area != self.area:
            lines += self._level(now, clock)
            self.area, self.level_start, self.level_since = area, now, clock
        return lines

    def game_over(self, number: int, now: Reading | None, clock: float) -> list[str]:
        """At Save and Exit of game `number`: the level left by it, then the game's line."""
        if now is None or self.game_start is None or self.first is None:
            self.game = self.game_start = self.area = self.level_start = None
            return [f'experience: game {number}: unread']
        lines = self._level(now, clock)
        self.games += 1
        hours = (clock - self.since) / 3600
        rate = f'{(now.experience - self.first.experience) / hours:,.0f}' if hours >= RATE_HOURS else '?'
        up = now.level - self.game_start.level
        level = f'level {now.level}{f", up {up}" if up else ""}'
        nxt = f', {now.to_next:,} to the next' if now.to_next is not None else ''
        lines.append(
            f'experience: game {number}: {gained(now.experience - self.game_start.experience)} ({level}{nxt}), '
            f'{rate} an hour over {self.games} game{"s" if self.games != 1 else ""}'
        )
        self.game = self.game_start = self.area = self.level_start = None
        return lines

    def _level(self, now: Reading, clock: float) -> list[str]:
        start, area = self.level_start, self.area
        if start is None or area is None or area in TOWN_IDS:  # no gain said for a town
            return []
        seconds = clock - self.level_since
        return [
            f'experience: {display_name(area)}: {gained(now.experience - start.experience)} in {seconds:.0f}s '
            f'(level {now.level})'
        ]
