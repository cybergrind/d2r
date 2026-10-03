"""Independent native and rendered-contract oracle for underlying Stormshield demand."""

import json

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.maintenance.trade_review_cases import REQUIRED
from pricing.knowledge.assessment.policies import stormshield_trade


IDENTITY = ('unique', 'Stormshield')
FIXED = {(36, 0): 35, (102, 0): 35, (0, 0): 30, (41, 0): 25, (43, 0): 60, (214, 0): 30}
VARIANTS = (
    REQUIRED
    | {(True, False, 1, c) for c in ('filled', 'unknown', None)}
    | {(True, False, 0, None), (True, False, 0, 'filled'), (True, False, 2, 'empty')}
)
PROPERTIES = (
    ('ac/lvl', None, None, 30),
    ('red-dmg%', 35, 35, None),
    ('str', 30, 30, None),
    ('indestruct', 1, 1, None),
    ('block2', 35, 35, None),
    ('res-ltng', 25, 25, None),
    ('block', 25, 25, None),
    ('res-cold', 60, 60, None),
    ('light-thorns', 10, 10, None),
)


def bind_policy(policy):
    reviewed = stormshield_trade.reviewed_date()
    return {
        **policy,
        'underlying_trade': json.loads(read_artifact(stormshield_trade.RULES)),
        'underlying_trade_validated_at': reviewed,
    }


def specification(policy, variants, stat_specs):
    if len(variants) != 1:
        return None
    definition = variants[0]
    base, game = definition.get('base_definition', {}), definition.get('game_definition', {})
    separate = policy.get('underlying_trade', {})
    level = stat_specs.get('214', {})
    if (
        (policy.get('quality'), policy.get('name')) != IDENTITY
        or policy.get('default_tier') != 'low'
        or (definition.get('rarity'), definition.get('name')) != IDENTITY
        or definition.get('base_code') != 'uit'
        or definition.get('base_name') != 'Monarch'
        or list(definition.get('base_codes', ())) != ['uit']
        or any(
            base.get(k) != v
            for k, v in {'code': 'uit', 'ultracode': 'uit', 'minac': 133, 'maxac': 148, 'gemsockets': 4}.items()
        )
        or game.get('code') != 'uit'
        or {k for k in game if k.startswith('prop')} != {f'prop{i}' for i in range(1, 10)}
        or any(
            (game.get(f'prop{i}'), game.get(f'min{i}'), game.get(f'max{i}'), game.get(f'par{i}')) != values
            for i, values in enumerate(PROPERTIES, 1)
        )
        or any(
            level.get(k) != v
            for k, v in {'name': 'item_armor_perlevel', 'op': 4, 'op_param': 3, 'op_base': 'level', 'shift': 0}.items()
        )
        or any(
            stat_specs.get(str(key[0]), {}).get(field) != 0
            for key in FIXED
            for field in ('shift', 'encode', 'parameter_bits')
        )
        or any(stat_specs.get(str(key[0]), {}).get('op') != 0 for key in FIXED if key != (214, 0))
        or stat_specs.get('31', {}).get('name') != 'armorclass'
        or stat_specs.get('36', {}).get('name') != 'damageresist'
        or stat_specs.get('102', {}).get('name') != 'item_fasterblockrate'
        or separate.get('id') != 'stormshield-underlying'
        or separate.get('scope') != 'SC / Non-Ladder / PC / RotW'
        or not policy.get('underlying_trade_validated_at')
        or policy['underlying_trade_validated_at'] != separate.get('reviewed_at')
        or len(separate.get('evidence_ids', [])) < 3
        or len(separate.get('guide_variants', {})) < 2
    ):
        return None
    return {'definition': definition, 'variants': VARIANTS}


def case_gap(cases, policy, spec):
    seen, missing, lower, higher = set(), set(), set(), set()
    for item, checks, signature in cases:
        stats = {(s, p): v for s, p, v in item['raw_stats']}
        if len(stats) != len(item['raw_stats']) or any(type(v) is not int for v in stats.values()):
            return 'Ambiguous Stormshield native capture.'
        identified, ethereal, sockets, contents = signature
        defense = stats.get((31, 0))
        benefits = all(stats.get(k, -1) >= v if k != (214, 0) else stats.get(k) == v for k, v in FIXED.items())
        qualifies = (
            identified is True
            and ethereal is False
            and item['complete'] is True
            and type(sockets) is int
            and sockets in (0, 1)
            and not (sockets == 0 and contents == 'filled')
            and contents in ('empty', 'filled', 'unknown', None)
            and type(defense) is int
            and defense >= 133
            and (not (sockets == 0 or contents == 'empty') or defense <= 148)
            and benefits
        )
        reason = 'Fixed damage reduction and blocking support Uber setups; ordinary defense still qualifies.'
        if sockets and contents != 'empty':
            reason += ' Assess inserts separately.'
        status = 'candidate' if qualifies else 'unresolved'
        lines = [{'text': 'Trade: candidate — ' + reason, 'tone': 'tier_low'}] if qualifies else []
        if checks.get('qualification') != {'status': status} or checks.get('lines') != lines:
            return 'Stormshield verdict or rendered text/color differs from native expectation.'
        if all(stats.get(k) == v for k, v in FIXED.items()):
            seen.add((signature, item['complete'], defense))
        if signature == (True, False, 0, 'empty') and item['complete'] is True and defense == 133:
            for key, value in FIXED.items():
                if any(stats.get(k) != v for k, v in FIXED.items() if k != key):
                    continue
                if key not in stats:
                    missing.add(key)
                elif stats[key] == value - 1:
                    lower.add(key)
                elif stats[key] == value + 1:
                    higher.add(key)
    required = {(v, True, 133) for v in VARIANTS}
    required.update(((True, False, s, 'empty'), True, d) for s in (0, 1) for d in (None, 132, 133, 148, 149))
    required.update(((True, False, 1, c), True, d) for c in ('filled', 'unknown', None) for d in (133, 148, 200))
    required.add(((True, False, 0, 'empty'), False, 133))
    if not required <= seen or any(keys != set(FIXED) for keys in (missing, lower, higher)):
        return 'Stormshield defense, variants or fixed-benefit boundaries are not all verified.'
    return None
