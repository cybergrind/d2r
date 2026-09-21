"""Player and mercenary health presentation."""

from .base import SampleWidget


class PlayerHealthWidget(SampleWidget):
    def render(self, *, now):
        state = self.state
        if (
            self.fresh(now)
            and state.current_raw is not None
            and state.maximum_raw
            and state.current_raw * 100 <= state.maximum_raw * self.config.player_health_percent
        ):
            return (f'{state.current_raw >> 8}/{state.maximum_raw >> 8}',)
        return ()


class MercHealthWidget(SampleWidget):
    def render(self, *, now):
        merc = self.state.merc
        if not self.fresh(now) or merc is None:
            return ()
        if not merc.alive:
            return ('merc dead',)
        if merc.life_fraction_raw * 100 < 32768 * self.config.merc_health_percent:
            prefix = '' if merc.life_fraction_raw == 32768 else '~'
            return (f'merc {prefix}{merc.current_raw >> 8}/{merc.maximum_raw >> 8}',)
        return ()
