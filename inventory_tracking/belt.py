"""Verified potion classification and four-row belt stock policy."""

from .models import PotionType


def potion_kind(class_id):
    if class_id in (530, 531):
        return PotionType.REJUVENATION
    if class_id in (602, 603, 604, 605, 606):
        return PotionType.HEALING
    return None


def column_shortages(contents):
    """Bottom potion defines each four-slot column; entirely empty means juv."""
    missing = {PotionType.REJUVENATION: 0, PotionType.HEALING: 0}
    for column in range(4):
        slots = contents[column::4]
        # If the bottom has a gap, use the lowest remaining item as the target.
        first = next((item for item in slots if item is not None), None)
        kind = PotionType.REJUVENATION if first is None else potion_kind(first)
        if kind is not None:
            missing[kind] += sum(potion_kind(item) != kind for item in slots)
    return missing[PotionType.REJUVENATION], missing[PotionType.HEALING]


def potion_count(contents, kind):
    return sum(potion_kind(item) == kind for item in contents)


def usable_cells(state, kind):
    return state.rejuvenation_cells if kind == PotionType.REJUVENATION else state.healing_cells
