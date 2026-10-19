"""The level the character came from and when, kept between hotkey presses (noted by runner.MacroRunner.poll)."""

import math


class Journey:
    def __init__(self) -> None:
        self.game: str | None = None
        self.area: int | None = None
        # (previous level, when this one was entered)
        self.last: tuple[int | None, float] = (None, -math.inf)

    def note(self, game: str | None, area: int | None, now: float) -> None:
        """`game` is None out of a game; `area` is None when the level could not be read."""
        if game != self.game:
            self.game, self.area, self.last = game, None, (None, -math.inf)
        if area is not None and area != self.area:
            self.last, self.area = (self.area, now), area

    def arrival(self, now: float) -> tuple[int | None, float]:
        """(the level the character was on before this one, seconds since it left it)."""
        previous, at = self.last
        return previous, now - at
