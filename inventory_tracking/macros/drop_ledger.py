"""Per-drop pickup tries and give-ups of a level run (`Hunter.drops`)."""

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
        """Why a spent drop is left, from its last try (an act expired mid-walk is not an empty click:
        run-0025-findings.md §2.3)."""
        tries = self.gathered.get(unit, 0)
        last = self.tried.get(unit)
        if last is None:
            return f'given up after {tries} tries: still on the ground after each'
        return f'given up after {tries} tries (the last: {last})'

    def forget(self) -> None:
        """Forget every give-up once Gheed's Fortune went to the stash (loop.py GHEED_STASH), so the refused charm is
        tried again."""
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
