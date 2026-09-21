"""Dynamic belt shortage presentation."""

from ...belt import column_shortages, potion_count
from ...models import PotionType
from .base import SampleWidget


class BeltWidget(SampleWidget):
    def render(self, *, now):
        contents = self.state.belt_contents
        if not self.fresh(now) or contents is None:
            return ()
        juv, hp = column_shortages(contents)
        if self.config.rejuvenation_target is not None:
            juv = max(0, self.config.rejuvenation_target - potion_count(contents, PotionType.REJUVENATION))
        if self.config.healing_target is not None:
            hp = max(0, self.config.healing_target - potion_count(contents, PotionType.HEALING))
        return tuple(f'{label} {count}' for label, count in [('juv', juv), ('hp', hp)] if count)
