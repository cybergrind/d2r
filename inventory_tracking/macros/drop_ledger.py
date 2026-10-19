"""What a level run tried and gave up on, drop by drop (macros/hunt.py `Hunter.drops`): the tries gone for each drop,
why the last took nothing, the one more try from near (`Hunter.again`), the give-ups said, the Gheed's swaps asked."""

from dataclasses import dataclass, field


__all__ = ['GATHER_TRIES', 'SAID_MOST', 'DropLedger']

GATHER_TRIES = 2  # times the sweep stops for one drop (and a level run goes for one, hunting/choice.py `side_drop`)
SAID_MOST = 200  # units a set remembers; cleared past it (units of games long left)


@dataclass
class DropLedger:
    gathered: dict[int, int] = field(default_factory=dict)  # unit -> times the sweep stopped or the run went for it
    tried: dict[int, str] = field(default_factory=dict)  # unit -> why the last try took nothing (the hands' Abort)
    retried: set[int] = field(default_factory=set)  # given up, then tried once more (`Hunter.again`)
    left_said: set[int] = field(default_factory=set)  # its giving up said
    swap_asked: set[int] = field(default_factory=set)  # the Gheed's swap asked for it (`Hunter.given_up_charm`)

    def spent(self, unit: int) -> bool:
        """Whether `unit` has had its GATHER_TRIES."""
        return self.gathered.get(unit, 0) >= GATHER_TRIES

    def given_up(self, unit: int) -> str:
        """Why a drop gone for GATHER_TRIES times is left: what its last try came to, as the hands said it (a priced
        act that expired mid-walk is not a click that took nothing: run-0025-findings.md §2.3)."""
        tries = self.gathered.get(unit, 0)
        last = self.tried.get(unit)
        if last is None:
            return f'given up after {tries} tries: still on the ground after each'
        return f'given up after {tries} tries (the last: {last})'

    def forget(self) -> None:
        """Every give-up forgotten: the player's Gheed's Fortune went onto a shared page (macros/loop.py GHEED_STASH),
        and the charm refused for it is tried again (13:57:50 on 2026-10-18: the new one, the same unit, was never
        tried, and the level run stood 45 s by it)."""
        for memory in (self.gathered, self.tried, self.retried, self.left_said, self.swap_asked):
            memory.clear()

    def first(self, memory: set[int], unit: int) -> bool:
        """Whether `unit` is new to `memory` (one of the sets), noted in it now."""
        if unit in memory:
            return False
        if len(memory) > SAID_MOST:
            memory.clear()
        memory.add(unit)
        return True
