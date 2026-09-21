"""Dynamic belt shortage presentation."""

from collections.abc import Sequence

from ...belt import column_shortages, potion_count
from ...config import BeltWidgetConfig
from ...models import PotionType
from .base import SampleWidget


class BeltWidget(SampleWidget[BeltWidgetConfig]):
    def render(self, *, now: float) -> Sequence[str]:
        if not self.config.enabled or not self.fresh(now) or self.state.belt is None:
            return ()
        contents = self.state.belt.contents
        juv, hp = column_shortages(contents)
        if self.config.rejuvenation_target is not None:
            juv = max(0, self.config.rejuvenation_target - potion_count(contents, PotionType.REJUVENATION))
        if self.config.healing_target is not None:
            hp = max(0, self.config.healing_target - potion_count(contents, PotionType.HEALING))
        return tuple(f'{label} {count}' for label, count in [('juv', juv), ('hp', hp)] if count)
