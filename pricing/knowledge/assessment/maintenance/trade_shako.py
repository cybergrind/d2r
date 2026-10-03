"""Published underlying-item evidence and native Shako report boundaries."""

import json

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.maintenance.trade_review_cases import REQUIRED
from pricing.knowledge.assessment.policies import shako_trade


IDENTITY = ('unique', 'Harlequin Crest')
VARIANTS = REQUIRED | {
    (True, False, 1, 'empty'),
    (True, False, 1, 'filled'),
    (True, False, 1, 'unknown'),
    (True, False, 2, 'empty'),
    (True, False, 0, 'filled'),
    (True, False, 0, None),
    (True, False, 1, None),
}
FIXED = {
    (127, 0): 2,
    (80, 0): 50,
    (36, 0): 10,
    (216, 0): 12 * 256,
    (217, 0): 12 * 256,
    (0, 0): 2,
    (1, 0): 2,
    (2, 0): 2,
    (3, 0): 2,
}
PROPERTIES = (
    ('allskills', 2, 2, None),
    ('hp/lvl', None, None, 12),
    ('mana/lvl', None, None, 12),
    ('mag%', 50, 50, None),
    ('red-dmg%', 10, 10, None),
    ('str', 2, 2, None),
    ('dex', 2, 2, None),
    ('vit', 2, 2, None),
    ('enr', 2, 2, None),
)


def bind_policy(policy):
    """Call inside the selected snapshot: baseline tiers cannot supply this proof."""
    reviewed = shako_trade.reviewed_date()
    return {
        **policy,
        'underlying_trade': json.loads(read_artifact(shako_trade.RULES)),
        'underlying_trade_validated_at': reviewed,
    }


def specification(policy, variants, stat_specs):
    if len(variants) != 1:
        return None
    definition = variants[0]
    base, game = definition.get('base_definition', {}), definition.get('game_definition', {})
    separate = policy.get('underlying_trade', {})
    spec = stat_specs.get('31', {})
    if (
        (policy.get('quality'), policy.get('name')) != IDENTITY
        or (definition.get('rarity'), definition.get('name')) != IDENTITY
        or definition.get('base_name') != 'Shako'
        or definition.get('base_code') != 'uap'
        or list(definition.get('base_codes', ())) != ['uap']
        or any(
            base.get(k) != v
            for k, v in {'code': 'uap', 'ultracode': 'uap', 'minac': 98, 'maxac': 141, 'gemsockets': 2}.items()
        )
        or game.get('code') != 'uap'
        or {k for k in game if k.startswith('prop')} != {f'prop{i}' for i in range(1, 10)}
        or any(
            (game.get(f'prop{i}'), game.get(f'min{i}'), game.get(f'max{i}'), game.get(f'par{i}')) != values
            for i, values in enumerate(PROPERTIES, 1)
        )
        or spec.get('name') != 'armorclass'
        or spec.get('op_base') is not None
        or any(spec.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits', 'op', 'op_param'))
        or separate.get('id') != 'shako-underlying'
        or separate.get('scope') != 'SC / Non-Ladder / PC / RotW'
        or not policy.get('underlying_trade_validated_at')
        or policy['underlying_trade_validated_at'] != separate.get('reviewed_at')
        or not separate.get('evidence_ids')
        or not separate.get('guide_entries')
    ):
        return None
    return {'definition': definition, 'variants': VARIANTS}


def case_gap(cases, policy, spec):
    seen = set()
    reason = 'Useful fixed skills, life/mana and magic find; low defense still qualifies.'
    for item, checks, signature in cases:
        stats = {(s, p): v for s, p, v in item['raw_stats']}
        if len(stats) != len(item['raw_stats']) or any(type(v) is not int for v in stats.values()):
            return 'Ambiguous Shako native capture.'
        if any(stats.get(k) != v for k, v in FIXED.items()):
            return 'Fixed native Shako benefits are missing from the report inputs.'
        identified, ethereal, sockets, contents = signature
        defense = stats.get((31, 0))
        known_defense = type(defense) is int and defense >= 98
        no_insert_defense = contents == 'empty' or sockets == 0
        candidate = (
            identified is True
            and ethereal is False
            and item['complete'] is True
            and type(sockets) is int
            and sockets in (0, 1)
            and not (contents == 'filled' and sockets == 0)
            and known_defense
            and (not no_insert_defense or defense <= 141)
        )
        status = 'candidate' if candidate else 'unresolved'
        rendered = reason + (' Assess inserts separately.' if contents != 'empty' and sockets else '')
        lines = [{'text': 'Trade: candidate — ' + rendered, 'tone': 'tier_med'}] if candidate else []
        if checks.get('qualification') != {'status': status} or checks.get('lines') != lines:
            return 'Shako verdict and rendered underlying-item text/color are not explicitly asserted.'
        seen.add((signature, item['complete'], defense))
    required = {(variant, True, 98) for variant in VARIANTS}
    required.update(((True, False, s, 'empty'), True, defense) for s in (0, 1) for defense in (None, 97, 98, 141, 142))
    required.update(
        ((True, False, 1, c), True, defense) for c in ('filled', 'unknown', None) for defense in (98, 141, 180)
    )
    required.add(((True, False, 0, 'empty'), False, 98))
    if not required <= seen:
        return 'Shako defense, socket payload or unknown capture boundaries are missing.'
    return None
