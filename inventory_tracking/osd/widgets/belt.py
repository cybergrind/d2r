"""Dynamic belt shortage presentation."""

from collections.abc import Sequence

from inventory_tracking.automation.priority import Level, StockWatch
from inventory_tracking.config import BELT, HEAL_PRIORITY, BeltWidgetConfig
from inventory_tracking.models import PotionType, State
from inventory_tracking.osd.widgets.base import SampleWidget
from inventory_tracking.tracking.belt import BeltColumns, column_shortages, potion_count, remember


class BeltWidget(SampleWidget[BeltWidgetConfig]):
    def reset(self) -> None:
        super().reset()
        # Each column's last kind this game: an emptied healing column still counts as healing missing.
        self.columns = BeltColumns()
        # Healing at or below the reserve (user, 2026-10-13: "something is wrong if we're empty").
        self.stock = StockWatch(HEAL_PRIORITY)

    def update(self, snapshot: State) -> None:
        super().update(snapshot)
        if snapshot.belt is not None and snapshot.session is not None:
            self.columns = remember(self.columns, snapshot.belt.contents, snapshot.session.core)
        self.stock.look(snapshot)

    def render(self, *, now: float) -> Sequence[str]:
        if not self.config.enabled or not self.fresh(now) or self.state.belt is None:
            return ()
        contents = self.state.belt.contents
        juv, hp = column_shortages(contents, self.columns, BELT.layout)
        if self.config.rejuvenation_target is not None:
            juv = max(0, self.config.rejuvenation_target - potion_count(contents, PotionType.REJUVENATION))
        if self.config.healing_target is not None:
            hp = max(0, self.config.healing_target - potion_count(contents, PotionType.HEALING))
        lines = tuple(f'{label} {count}' for label, count in [('juv', juv), ('hp', hp)] if count)
        if not self.stock.alarm:
            return lines
        if self.stock.level == Level.EMPTY:
            return ('HP EMPTY', *lines)
        return (f'HP LOW: {self.stock.healing} left', *lines)
