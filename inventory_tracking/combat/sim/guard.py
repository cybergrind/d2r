"""A guard on the character: a pool that takes some kinds of a blow's damage before the resistances and, while
it stands, stuns a monster whose melee blow lands. The rules are the client's (rca/2026-10-13/re/notes-absorb.md);
the skill, pool and stun are a build's. Only blows of the client-rule types (sim/casters.py) are guarded: the
fitted types were fitted with the guard up. The rules in full: combat/history/sim-guard.md.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from inventory_tracking.game.layout import UNIQUE_FLAG  # the type flag the routine tests (monster data +0x1A bit 3)


UNIQUE_STUN = 0.10  # [code] ai_d2_stun_apply 0x14038C2F0: a monster with type flag 8 only when roll % 100 >= 90
STUN_MOST = 250  # [code] frames: the same routine's cap
# [table] monstats.txt rows with `boss` 1: never stunned. By the client's class id (`*hcIdx`), not the row's place
# (one less past the expansion's divider row; rca/2026-10-13/diablo.md "Hooked in").
BOSSES = frozenset(
    (156, 211, 229, 242, 243, 250, 256, 267, 333, 365, 526, 544, 546, 547, 548, 549, 550, 559, 570,
     704, 705, 706, 707, 708, 709, 745, 746, 747)
)  # fmt: skip


@dataclass(frozen=True)
class GuardRule:
    """What a build's guard is: the points its pool holds when set, the kinds of damage it takes, and the frames
    a monster whose melee blow lands is stunned while it stands (0: none)."""

    most: float
    kinds: tuple[str, ...]
    stun: int = 0


class Guard:
    """The guard's state in a play: what is left of the pool, and the tallies of what it did."""

    def __init__(self, rule: GuardRule, up: bool = False) -> None:
        self.rule = rule
        self.left = rule.most if up else 0.0
        self.sets = 0  # times it was set (cast)
        self.falls = 0  # times the pool ran out
        self.taken = 0.0  # points the pool took, raw
        self.stuns = 0  # monsters it stunned

    @property
    def up(self) -> bool:
        return self.left > 0

    def set(self) -> None:
        """Cast: the pool is at its most again."""
        self.left = self.rule.most
        self.sets += 1

    def take(self, parts: Mapping[str, float]) -> dict[str, float]:
        """A blow's parts in raw points after the pool took what it takes of them."""
        found = dict(parts)
        if not self.up:
            return found
        for kind in self.rule.kinds:
            points = found.get(kind, 0.0)
            if points <= 0:
                continue
            took = min(points, self.left)
            found[kind] = points - took
            self.left -= took
            self.taken += took
            if self.left <= 0:
                self.left = 0.0
                self.falls += 1
                break
        return found

    def stun_frames(self, txt: int, flags: int, moves: bool, roll: Callable[[], float]) -> int:
        """The frames a monster of `txt` with `flags` whose melee blow just landed is stunned for (0: none). `roll`
        is drawn only for a unique, as the game rolls only then."""
        if not self.up or self.rule.stun <= 0 or txt in BOSSES or not moves:
            return 0
        if flags & UNIQUE_FLAG and roll() >= UNIQUE_STUN:
            return 0
        self.stuns += 1
        return min(self.rule.stun, STUN_MOST)
