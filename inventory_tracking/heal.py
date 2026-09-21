"""Health policy; potion availability and execution belong to PotionsController."""

from .models import Actor, PotionType


class HealController:
    def __init__(self, config, potions):
        if config != potions.config:
            raise ValueError('Healing and potion controllers must share configuration')
        self.config = config
        self.potions = potions

    def step(self, state):
        choices = []
        current, maximum = state.current_raw, state.maximum_raw
        if self.config.actor == Actor.MERC:
            merc = state.merc
            current, maximum = (merc.life_fraction_raw, 32768) if merc and merc.alive else (None, None)
        if current is not None and maximum is not None and 0 < current <= maximum:
            choices = [
                potion
                for potion in (PotionType.REJUVENATION, PotionType.HEALING)
                if current * 100 < maximum * self.config.thresholds[potion]
            ]
        # Pending acknowledgements must progress even when health is unavailable/full.
        return self.potions.step(state, choices)
