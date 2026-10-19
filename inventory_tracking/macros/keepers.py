"""Items the loop never sells whatever the appraisal says, judged by their own stats.

The player, 16:50 on 2026-10-18: "Rare amulets with +FCR, +2 skills, +life are good, and other combinations may be; a
high vendor price alone does not make one a keeper." The pricing rule built from it (+1 class or +2 tree with 10 FCR and
20+ life) is narrower than those words, and at 03:48 on 2026-10-19 the appraisal called two rare amulets `vendor` that
the words keep: Corruption Scarab (+41 life, fire resistance 35%) and Havoc Torc (+59 life, +1 Eldritch Skills); both
were sold. This guard reads the words as they are: a rare or crafted amulet with any faster cast rate, any life or two
skills or more is no junk; it goes to the stash as a keeper.

Stat ids are itemstatcost.txt's (pricing/raw/game-excel): maxhp 7 (ValShift 8), item_fastercastrate 105,
item_allskills 127, item_addclassskills 83, item_addskill_tab 188. `World.item_stats` keys them by id alone (the
skill's class or tree is not kept), so +2 to any class or any tree counts as two skills.
"""

from collections.abc import Mapping

from inventory_tracking.items.metadata import item_base
from inventory_tracking.macros.game.records import Carried


RARE, CRAFTED = 6, 8  # ItemData quality (macros/junk.py)
AMULET_CODE = 'amu'
LIFE, FCR, ALL_SKILLS, CLASS_SKILLS, TREE_SKILLS = 7, 105, 127, 83, 188
LIFE_SHIFT = 8  # maxhp is kept in 256ths of a point
SKILLS = 2  # "+2 skills"


def amulet_keeper(item: Carried, stats: Mapping[int, int]) -> str | None:
    """Why a rare or crafted amulet is kept by the player's words (the module text), None when nothing keeps it. Its
    stats unread (`stats` empty): kept, for a sale cannot be undone."""
    base = item_base(item.txt)
    if base is None or base.get('code') != AMULET_CODE or item.quality not in (RARE, CRAFTED):
        return None
    if not stats:
        return 'its stats unread'
    if stats.get(FCR, 0) > 0:
        return f'{stats[FCR]}% faster cast rate'
    if stats.get(LIFE, 0) > 0:
        return f'+{stats[LIFE] >> LIFE_SHIFT} life'
    skills = max(stats.get(ALL_SKILLS, 0), stats.get(CLASS_SKILLS, 0), stats.get(TREE_SKILLS, 0))
    if skills >= SKILLS:
        return f'+{skills} skills'
    return None
