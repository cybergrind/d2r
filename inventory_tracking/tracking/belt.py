"""Verified potion classification and four-row belt stock policy."""

from collections.abc import Hashable, Sequence
from dataclasses import dataclass

from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import BELT_COLUMNS, HEALING_POTIONS, REJUVENATION_POTIONS


# The kind of a column never seen holding anything this game, with no layout configured (config.BELT).
UNSEEN = PotionType.REJUVENATION


def potion_kind(class_id: int | None) -> PotionType | None:
    if class_id in REJUVENATION_POTIONS:
        return PotionType.REJUVENATION
    if class_id in HEALING_POTIONS:
        return PotionType.HEALING
    return None


@dataclass(frozen=True)
class BeltColumns:
    """What each belt column last held, for one game and belt, so an emptied column keeps its kind
    (rca/2026-10-13/potions-findings.md §2.1). `kinds[c]`: the kind of column c's lowest potion when it last
    held one (None: never seen, or not a potion). Folded by `remember`, read by `column_shortages`."""

    game: Hashable = None  # whose belt: the caller's identity of the game and character
    rows: int | None = None  # the belt's rows when the caller knows them; another size forgets the kinds
    kinds: tuple[PotionType | None, ...] = (None,) * BELT_COLUMNS


def lowest(contents: Sequence[int | None], column: int) -> int | None:
    """The item a four-slot column is read by: its lowest one (a gap at the bottom is skipped)."""
    return next((item for item in contents[column::BELT_COLUMNS] if item is not None), None)


def remember(
    columns: BeltColumns, contents: Sequence[int | None], game: Hashable, rows: int | None = None
) -> BeltColumns:
    """`columns` after a look at the belt `contents` of `game`: a column holding something takes the kind of
    its lowest item, an empty one keeps what it last held. Another game or belt size starts afresh."""
    if game != columns.game or rows != columns.rows:
        columns = BeltColumns(game, rows)
    kinds = tuple(
        known if (first := lowest(contents, column)) is None else potion_kind(first)
        for column, known in enumerate(columns.kinds)
    )
    return columns if kinds == columns.kinds else BeltColumns(game, rows, kinds)


def column_shortages(
    contents: Sequence[int | None],
    columns: BeltColumns | None = None,
    layout: Sequence[PotionType] | None = None,
) -> tuple[int, int]:
    """(rejuvenation, healing) missing from the belt. Bottom potion defines each four-slot column; an
    entirely empty one is of the configured `layout`'s kind if one is set, else of the kind it last
    held (`columns`, the belt's history), else UNSEEN."""
    missing = {PotionType.REJUVENATION: 0, PotionType.HEALING: 0}
    for column in range(BELT_COLUMNS):
        slots = contents[column::BELT_COLUMNS]
        first = lowest(contents, column)
        if first is not None:
            kind = potion_kind(first)
        elif layout is not None:
            kind = layout[column]
        else:
            kind = (columns.kinds[column] if columns is not None else None) or UNSEEN
        if kind is not None:
            missing[kind] += sum(potion_kind(item) != kind for item in slots)
    return missing[PotionType.REJUVENATION], missing[PotionType.HEALING]


def potion_count(contents: Sequence[int | None], kind: PotionType) -> int:
    return sum(potion_kind(item) == kind for item in contents)


def column_stock(contents: Sequence[int | None], column: int, kind: PotionType) -> int:
    """Potions of `kind` stacked in hotkey column 1..4."""
    return potion_count(contents[column - 1 :: BELT_COLUMNS], kind)
