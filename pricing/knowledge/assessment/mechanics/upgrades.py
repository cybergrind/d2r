"""Bounded unique/set/rare upgrade routes for the configured Non-Ladder economy.

Recipes: d2data fc469993502d cubemain129-136 and151-154. Set recipes became
available online Non-Ladder with D2R2.6 (Blizzard article23899624):
https://news.blizzard.com/en-gb/article/23899624/diablo-ii-resurrected-ladder-season-three-has-concluded
No hypothetical defense roll, requirement total or sale price is calculated.
"""

from pricing.knowledge.assessment.adapters.capture import bases_by_code
from pricing.knowledge.assessment.domain.upgrades import UpgradePath
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.mechanics.base_tiers import base_at_tier, base_tier
from pricing.knowledge.assessment.registry import classify


# Step recipe IDs for unique/set, consumed ingredients, added level penalty.
RECIPES = {
    ('weapon', 'Exceptional'): ('129', '151', ('Ral Rune', 'Sol Rune', 'Perfect Emerald'), 5),
    ('armor', 'Exceptional'): ('130', '152', ('Tal Rune', 'Shael Rune', 'Perfect Diamond'), 5),
    ('weapon', 'Elite'): ('131', '153', ('Lum Rune', 'Pul Rune', 'Perfect Emerald'), 7),
    ('armor', 'Elite'): ('132', '154', ('Ko Rune', 'Lem Rune', 'Perfect Diamond'), 7),
}
RARE_RECIPES = {
    ('weapon', 'Exceptional'): ('133', ('Ort Rune', 'Amn Rune', 'Perfect Sapphire'), 5),
    ('armor', 'Exceptional'): ('134', ('Ral Rune', 'Thul Rune', 'Perfect Amethyst'), 5),
    ('weapon', 'Elite'): ('135', ('Fal Rune', 'Um Rune', 'Perfect Sapphire'), 7),
    ('armor', 'Elite'): ('136', ('Ko Rune', 'Pul Rune', 'Perfect Amethyst'), 7),
}


def upgrade_paths(facts):
    if facts.rarity not in ('unique', 'set', 'rare') or facts.identified is not True or facts.runeword:
        return ()
    if facts.rarity != 'rare':
        definition, _ = resolve_named_definition(facts)
        if definition is None:
            return ()
    family = classify(facts)[0]
    if family in ('armor', 'helm', 'shield', 'accessory'):
        family = 'armor'
    if family not in ('weapon', 'armor'):
        return ()
    current_tier = base_tier(facts.base_code)
    if current_tier not in ('Normal', 'Exceptional'):
        return ()
    targets = ('Exceptional', 'Elite') if current_tier == 'Normal' else ('Elite',)
    current = facts.base_code
    steps = []
    paths = []
    bases = bases_by_code()
    for tier in targets:
        target = base_at_tier(current, tier)
        if not target or target not in bases:
            break
        if facts.rarity == 'rare':
            row_id, resources, penalty = RARE_RECIPES[family, tier]
        else:
            unique_id, set_id, resources, penalty = RECIPES[family, tier]
            row_id = unique_id if facts.rarity == 'unique' else set_id
        steps.append(
            {
                'action': 'upgrade_base',
                'source_code': current,
                'target_code': target,
                'target_name': bases[target]['name'],
                'resources': resources,
                'level_requirement_penalty': penalty,
                'source': f'third-parties/d2data/json/cubemain.json#{row_id}',
            }
        )
        paths.append(UpgradePath(facts.base_code, target, bases[target]['name'], tuple(steps)))
        current = target
    return tuple(paths)
