"""A scripted sampler for the recording process's tests (takes/recorder_process.py `Config.sampler`): made in the
child from its `Fed`, a character in the Chaos Sanctuary while a game is bound."""

from inventory_tracking.game.records import Player, World
from inventory_tracking.takes.record import Sample


class Scripted:
    def __init__(self, fed) -> None:
        self.fed = fed

    def __call__(self) -> Sample | None:
        if self.fed.game is None:
            return None
        world = World(True, (), 'game-1', (), player=Player(1, 'Tester', 1, 108, 7800.0, 5500.0, None))
        return Sample(world, macro=self.fed.working, macro_state=self.fed.macro_state)


def scripted(fed) -> Scripted:
    return Scripted(fed)


class Walking(Scripted):
    """The character in the area the service's macro state names (`{'area': n}`), 108 before: a take per area."""

    def __call__(self) -> Sample | None:
        if self.fed.game is None:
            return None
        area = (self.fed.macro_state or {}).get('area', 108)
        world = World(True, (), 'game-1', (), player=Player(1, 'Tester', 1, area, 7800.0, 5500.0, None))
        return Sample(world, macro=self.fed.working, macro_state=self.fed.macro_state)


def walking(fed) -> Walking:
    return Walking(fed)
