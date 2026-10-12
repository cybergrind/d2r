"""Health policy; potion availability and execution belong to PotionsController."""

from collections import deque

from inventory_tracking.automation.potions import PotionsController
from inventory_tracking.config import HealingConfig
from inventory_tracking.models import PotionResult, PotionType, SessionIdentity, State
from inventory_tracking.tracking.belt import potion_kind


class HealController:
    def __init__(self, config: HealingConfig, potions: PotionsController) -> None:
        if config != potions.config:
            raise ValueError('Healing and potion controllers must share configuration')
        self.config = config
        self.potions = potions
        # The actor's life over the last burst_window seconds of one game: (sampled at, share of the most life).
        self.session: SessionIdentity | None = None
        self.recent: deque[tuple[float, float]] = deque()

    def burst(self, state: State, share: float) -> bool:
        """Whether the life fell by the burst share within the window, counted from the most it was in it."""
        if state.session != self.session:
            self.session = state.session
            self.recent.clear()
        while self.recent and state.sampled_at - self.recent[0][0] > self.config.burst_window:
            self.recent.popleft()
        most = max((seen for _, seen in self.recent), default=share)
        self.recent.append((state.sampled_at, share))
        return bool(self.config.burst_share) and (most - share) * 100 >= self.config.burst_share

    @staticmethod
    def rejuvenations(state: State) -> int:
        """The rejuvenation potions on the belt, every row; none where the belt is unread."""
        contents = state.belt.contents if state.belt is not None else ()
        return sum(1 for item in contents if potion_kind(item) == PotionType.REJUVENATION)

    def step(self, state: State) -> PotionResult:
        choices = []
        health = state.health_for(self.config.actor)
        if health is not None and 0 < health[0] <= health[1]:
            current, maximum = health
            choices = [
                potion
                for potion in (PotionType.REJUVENATION, PotionType.HEALING)
                if current * 100 < maximum * self.config.thresholds[potion]
            ]
            if self.burst(state, current / maximum):
                # A healing potion where the belt holds no rejuvenation: `PotionsController` takes the first it has.
                choices = [PotionType.REJUVENATION, PotionType.HEALING]
            if self.config.rejuvenation_reserve and self.rejuvenations(state) <= self.config.rejuvenation_reserve:
                choices = [potion for potion in choices if potion != PotionType.REJUVENATION]
        # Pending acknowledgements must progress even when health is unavailable/full.
        return self.potions.step(state, choices)
