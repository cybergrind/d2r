"""Items the loop never sells whatever the appraisal says, judged by their own stats.

"Rare amulets with +FCR, +2 skills, +life are good, and other combinations may be" (the player, 2026-10-18). The
pricing rule is narrower (two such amulets were sold as `vendor` on 2026-10-19 03:48), so this guard reads the words
as they are: a rare or crafted amulet with any FCR, any life or 2+ skills is a keeper.

Stat ids from itemstatcost.txt (pricing/raw/game-excel). `World.item_stats` keys by id alone, so +2 to any class or
tree counts as two skills.
"""

from collections.abc import Mapping

from inventory_tracking.game.records import Carried
from inventory_tracking.items.metadata import item_base


RARE, CRAFTED = 6, 8  # ItemData quality (macros/junk.py)
AMULET_CODE = 'amu'
LIFE, FCR, ALL_SKILLS, CLASS_SKILLS, TREE_SKILLS = 7, 105, 127, 83, 188
LIFE_SHIFT = 8  # maxhp is kept in 256ths of a point
SKILLS = 2  # "+2 skills"


# The town's keep rules hold it as the wants row rare-amulet-fcr-life-skills (loot/build_wants.py G11) when TOWN_DECIDES
# is on (loot/keep.py, M6, 2026-10-20); it stays the guard behind engine.py `protected` (run.kept_item: "protected
# amulets still spared", the player's 16:55 plan) and loot/today.py's. Delete after the 30-cycle check
def amulet_keeper(item: Carried, stats: Mapping[int, int]) -> str | None:
    """Why a rare or crafted amulet is kept, or None. Unread stats keep it: a sale cannot be undone."""
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
