"""Original fixed IK components: native bonuses and defense, no roll premium."""

from pricing.knowledge.assessment.maintenance.trade_fixed_armor import _fixed_properties, _variant_fields, _variant_rule
from pricing.knowledge.assessment.maintenance.trade_review_cases import LEGAL, REQUIRED


SPECS = {
    "Immortal King's Forge": {
        'base': 'War Gauntlets',
        'code': 'xhg',
        'upgrade': 'Ogre Gauntlets',
        'upgrade_code': 'uhg',
        'type': 'glov',
        'defense': (43, 53),
        'props': {'ac': 65, 'str': 20, 'dex': 20},
        'partial': {'swing2': 25, 'ac': 120, 'lifesteal': 10, 'manasteal': 10, 'freeze': 2},
        'stats': {(0, 0): 20, (2, 0): 20, (201, (38 << 6) | 4): 12},
        'totals': {108, 118, 228, 238},
    },
    "Immortal King's Detail": {
        'base': 'War Belt',
        'code': 'zhb',
        'upgrade': 'Colossus Girdle',
        'upgrade_code': 'uhc',
        'type': 'belt',
        'defense': (41, 52),
        'props': {'ac': 36, 'res-fire': 28, 'res-ltng': 31, 'str': 25},
        'partial': {'ac': 105, 'balance2': 25, 'ac%': 100, 'red-dmg%': 20, 'skilltab': 2},
        'stats': {(0, 0): 25, (39, 0): 28, (41, 0): 31},
        'totals': {89},
    },
}
VARIANTS = REQUIRED | {(True, False, 0, 'filled')}


def specification(policy, variants, stat_specs):
    config = SPECS.get(policy.get('name'))
    if config is None or policy.get('quality') != 'set' or len(variants) != 1:
        return None
    definition = variants[0]
    base = definition.get('base_definition', {})
    game = definition.get('game_definition', {})
    trade = policy.get('trade_qualification', {})
    original = dict(game)
    if policy['name'] == "Immortal King's Forge":
        if (game.get('prop4'), game.get('par4'), game.get('min4'), game.get('max4')) != ('gethit-skill', 38, 12, 4):
            return None
        original.pop('prop4')
    elif game.get('apar5a') != 13:
        return None
    stat = stat_specs.get('31', {})
    if (
        (definition.get('rarity'), definition.get('name')) != ('set', policy['name'])
        or definition.get('base_name') != config['base']
        or definition.get('base_code') != config['code']
        or list(definition.get('base_codes', ())) != [config['code']]
        or any(
            base.get(k) != v
            for k, v in {
                'code': config['code'],
                'ultracode': config['upgrade_code'],
                'type': config['type'],
                'gemsockets': 0,
            }.items()
        )
        or (base.get('minac'), base.get('maxac')) != config['defense']
        or game.get('item') != config['code']
        or game.get('add func') != 2
        or not _fixed_properties(original, 'prop', 'min', 'max', config['props'])
        or not _fixed_properties(game, 'aprop', 'amin', 'amax', config['partial'])
        or stat.get('name') != 'armorclass'
        or stat.get('op_base') is not None
        or any(stat.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits', 'op', 'op_param'))
        or trade.get('material_stats') != []
        or trade.get('bands') != []
        or trade.get('default_status') != 'candidate'
        or policy.get('overrides')
        or policy.get('variant_rules')
        or not _variant_rule(policy['valid_if'], config['code'])
        or not _variant_rule(trade['valid_if'], config['code'])
        or not {'ethereal', 'sockets', 'socket_contents', 'base_code'}
        <= (_variant_fields(policy['valid_if']) | _variant_fields(trade['valid_if']))
    ):
        return None
    from pricing.knowledge.artifacts import read_artifact
    from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG
    from pricing.knowledge.market_base_catalog import equipment_index

    index, _ = equipment_index(read_artifact(CATALOG))
    upgraded = [r for r in index.values() if r['base_code'] == config['upgrade_code']]
    if len(upgraded) != 1 or upgraded[0]['name'] != config['upgrade']:
        return None
    return {'definition': definition, 'config': config, 'variants': VARIANTS, 'upgraded_base': config['upgrade']}


def case_gap(cases, policy, spec):
    config = spec['config']
    seen = set()
    totals = set()
    upgraded = False
    for item, checks, signature in cases:
        original = item['base'] == config['base']
        if not original and item['base'] != config['upgrade']:
            return 'Unreviewed IK base variant.'
        candidate = original and signature == LEGAL
        status = 'candidate' if candidate else 'unresolved'
        lines = (
            [{'text': 'Trade: candidate — ' + policy['trade_qualification']['default_reason'], 'tone': 'tier_low'}]
            if candidate
            else []
        )
        if checks.get('qualification') != {'status': status} or checks.get('lines') != lines:
            return 'IK component verdict, text and color are not asserted.'
        captured = {(s, p): v for s, p, v in item['raw_stats']}
        if len(captured) != len(item['raw_stats']) or any(type(v) is not int for v in captured.values()):
            return 'Ambiguous native IK stats.'
        if any(captured.get(k) != v for k, v in config['stats'].items()):
            return 'Missing or changed fixed IK bonuses.'
        if original:
            seen.add(signature)
        elif signature == LEGAL:
            upgraded = True
        if candidate:
            defense = captured.get((31, 0))
            valid = (
                defense == 89
                if policy['name'] == "Immortal King's Detail"
                else (defense in range(108, 119) or defense in range(228, 239))
            )
            if not valid:
                return 'Unreviewed native IK defense outcome.'
            totals.add(defense)
    if not seen >= VARIANTS or not config['totals'] <= totals or not upgraded:
        return 'IK original, upgraded, defense or unknown variant reports are missing.'
    return None
