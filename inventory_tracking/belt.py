"""Verified potion classification and four-row belt stock policy."""

from collections.abc import Sequence

from .layout import BELT_COLUMNS, HEALING_POTIONS, REJUVENATION_POTIONS
from .models import PotionType


def potion_kind(class_id: int | None) -> PotionType | None:
    if class_id in REJUVENATION_POTIONS:
        return PotionType.REJUVENATION
    if class_id in HEALING_POTIONS:
        return PotionType.HEALING
    return None


def column_shortages(contents: Sequence[int | None]) -> tuple[int, int]:
    """Bottom potion defines each four-slot column; entirely empty means juv."""
    missing = {PotionType.REJUVENATION: 0, PotionType.HEALING: 0}
    for column in range(BELT_COLUMNS):
        slots = contents[column::BELT_COLUMNS]
        # If the bottom has a gap, use the lowest remaining item as the target.
        first = next((item for item in slots if item is not None), None)
        kind = PotionType.REJUVENATION if first is None else potion_kind(first)
        if kind is not None:
            missing[kind] += sum(potion_kind(item) != kind for item in slots)
    return missing[PotionType.REJUVENATION], missing[PotionType.HEALING]


def potion_count(contents: Sequence[int | None], kind: PotionType) -> int:
    return sum(potion_kind(item) == kind for item in contents)
