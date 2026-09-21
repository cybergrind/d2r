"""Optional secondary staff charge and town repair reminder."""

from .base import SampleWidget


class TeleportWidget(SampleWidget):
    def render(self, *, now):
        observation = self.state.teleport
        charges = observation.value
        if not self.config.teleport.enabled or not observation.fresh(now, self.config.max_age) or charges is None:
            return ()
        if charges.current == charges.maximum:
            return ()
        location = self.state.location
        repair = (
            self.config.teleport.show_repair_in_town
            and location.fresh(now, self.config.max_age)
            and location.value is not None
            and location.value.in_town
        )
        low = charges.current * 100 < charges.maximum * self.config.teleport.low_percent
        if repair or low:
            return (f'tele {charges.current}/{charges.maximum}' + (' repair' if repair else ''),)
        return ()
