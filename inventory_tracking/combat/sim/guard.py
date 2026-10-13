"""A guard on the character: a pool that takes some kinds of a blow's damage before the resistances, and while it
stands stuns a monster whose melee blow lands on the character. The rules are the client's, read in the decrypted
executable (rca/2026-10-13/re/notes-absorb.md); which skill sets a guard, its pool and its stun are a build's.

[code] the pool (event 11 `absorbdamage`, run by the damage resolve before the flat reductions, the resistances
and the absorb percentages):

- it takes only the kinds the rule names, each up to what is left of the pool: a blow's part of such a kind
  loses min(left, part), the pool as much;
- at 0 the state is removed: the guard is down until the build sets it again; a set always refills it to its
  most (the old state node is dropped and a new one made with the pool at its most);
- it has no length: it stands until it is used up or set again.

[code] the stun (event 1 `damagedinmelee`, run after the resolve, for a blow that hit, also one the pool took
whole; gone with the state, so not for the blow that took the pool to 0 [inferred: the remove callback drops the
state's handlers, the free path that calls it not read]): the striker is stunned for the rule's frames, at most
STUN_MOST; a monster with the unique flag only on UNIQUE_STUN of the character's rolls, never a boss (monstats
`boss`, BOSSES), never one that cannot move (monstats `Velocity` 0). A stunned monster neither thinks, walks, swings
nor casts until the stun is over [take: in the records of 2026-10-13 a Doom Knight's swing is followed by the
get-hit mode with state 21 on, then the neutral mode, then a walk 3.1 to 3.6 s later at the samples' resolution;
the AI's own test of the state not read], then thinks at once [inferred].

Which blows: only those of the types played by the client's own rules (sim/casters.py, a walker with a mind):
the fitted types' chances to take life and their cadence were fitted to takes in which the guard mostly stood, so
it is in them already (sim/casters.py's module text; rca/2026-10-13/sim-casters.md section 5).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass


UNIQUE_FLAG = 0x08  # the type flag the routine tests (monster data +0x1A bit 3; macros/world.py LEADER_FLAGS)
UNIQUE_STUN = 0.10  # [code] ai_d2_stun_apply 0x14038C2F0: a monster with type flag 8 only when roll % 100 >= 90
STUN_MOST = 250  # [code] frames: the same routine's cap
# [table] monstats.txt rows with `boss` 1 (pricing/raw/game-excel, the extraction of 2026-10-13): never stunned
# (the routine tests the row's boss flag). By the client's class id (`*hcIdx`), which past the expansion's divider
# row is one less than the row's place among the data rows (2026-10-13, rca/2026-10-13/diablo.md "Hooked in": 527
# 545 547-551 560 571 705-710 746-748 were places: Nihlathak, Baal, the Putrid Defilers, the uber bosses and the
# colossi were off by one, 545 Baal Taunt and 710 were in).
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
        """The frames a monster of `txt` with type `flags` whose melee blow just landed is stunned for, 0 for none:
        nothing while the guard is down; `moves` False for a type that cannot move; `roll` the character's
        generator (0 to 1), drawn only for a unique, as the game rolls only then."""
        if not self.up or self.rule.stun <= 0 or txt in BOSSES or not moves:
            return 0
        if flags & UNIQUE_FLAG and roll() >= UNIQUE_STUN:
            return 0
        self.stuns += 1
        return min(self.rule.stun, STUN_MOST)
