"""Quest socket outcomes for magic and higher quality equipment.

Pinned D2MOO SUnitNpc.cpp 2273-2291: magic rolls1..min(max,2);
rare/set/unique/crafted get one. Base/type caps come from the portable utility KB.
"""

from dataclasses import replace

from pricing.knowledge.assessment.base_use import recipe_index
from pricing.knowledge.assessment.domain.comparison_requests import ComparisonRequest
from pricing.knowledge.assessment.domain.preparation import PreparationOption
from pricing.knowledge.assessment.mechanics.preparation_costs import with_costs


def quality_socket_requests(facts, contract):
    if contract.policy not in ('named', 'affixed') or facts.rarity not in ('magic', 'rare', 'crafted', 'unique', 'set'):
        return ()
    candidates = [
        r
        for r in recipe_index().by_base.get(facts.base_name, ())
        if r.get('base_code') == facts.base_code and r['details'].get('rule') == 'socket_potential'
    ]
    if len(candidates) != 1:
        return ()
    rule = candidates[0]
    caps = list(rule['details']['larzuk_unknown_ilvl']['maximum_by_ilvl_bracket'])
    if facts.item_level is not None:
        caps = [caps[0 if facts.item_level <= 25 else 1 if facts.item_level <= 40 else 2]]
    if not caps or any(type(cap) is not int or cap < 1 for cap in caps):
        return ()
    caps = sorted({min(cap, 2 if facts.rarity == 'magic' else 1) for cap in caps})
    results = []
    for target in range(1, max(caps) + 1):
        outcomes = tuple({'maximum': cap, 'success_weight': int(target <= cap), 'denominator': cap} for cap in caps)
        option = with_costs(
            PreparationOption(
                'empty sockets',
                target,
                'larzuk',
                'possible' if caps == [1] else 'conditional',
                ('item_level',) if len(caps) > 1 else (),
                outcomes,
            ),
            facts,
        )
        if caps != [1]:
            option = replace(option, action='larzuk_magic')
        action = option.to_dict()
        action['source'] = 'third-parties/D2MOO/source/D2Game/src/UNIT/SUnitNpc.cpp#2273-2291'
        action['socket_cap_source'] = rule['source_locator']
        results.append(
            ComparisonRequest(
                f'quest_quality_{target}',
                f'item_after_quest_{target}',
                replace(contract, sockets=target).to_dict(),
                state='prepared',
                preparation=action,
            )
        )
    return tuple(results)
