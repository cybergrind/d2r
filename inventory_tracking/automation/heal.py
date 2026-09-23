"""Health policy; potion availability and execution belong to PotionsController."""

from inventory_tracking.automation.potions import PotionsController
from inventory_tracking.config import HealingConfig
from inventory_tracking.models import PotionResult, PotionType, State


class HealController:
    def __init__(self, config: HealingConfig, potions: PotionsController) -> None:
        if config != potions.config:
            raise ValueError('Healing and potion controllers must share configuration')
        self.config = config
        self.potions = potions

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
        # Pending acknowledgements must progress even when health is unavailable/full.
        return self.potions.step(state, choices)
