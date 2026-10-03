"""Evidence-only original-base proof for reviewed set items.

Defense 1855 is total defense. Bonus field 399 and ambiguous Normal labels
cannot establish a base. This helper never rewrites the cached source row.
"""

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.handlers.definitions import named_definitions
from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG, base_at_tier, base_tier
from pricing.knowledge.market_base_catalog import equipment_base, equipment_index


MODE = 'original_total_defense'
REVIEWED_PROPERTIES = {
    "Trang-Oul's Claws": {'ac', 'cast3', 'res-cold', 'skilltab', 'extra-pois'},
    "Tal Rasha's Fine-Spun Cloth": {'ease', 'mana', 'dex', 'dmg-to-mana', 'mag%', 'ac', 'cast2'},
    "Bane's Authority": {'cast1', 'hp', 'enr'},
}


def _flat_bonus(definition):
    bonus = 0
    for key, value in definition['game_definition'].items():
        conditional = key.startswith('aprop')
        if not (conditional or key.startswith('prop')):
            continue
        if value not in REVIEWED_PROPERTIES[definition['name']]:
            return None
        if value == 'ac':
            suffix = key.removeprefix('aprop' if conditional else 'prop')
            prefix = 'a' if conditional else ''
            low = definition['game_definition'].get(f'{prefix}min{suffix}')
            high = definition['game_definition'].get(f'{prefix}max{suffix}')
            if type(low) is not int or type(high) is not int or low < 0 or low != high:
                return None
            # Positive conditional bonuses cannot reduce an upgraded base to
            # an original total. They are not part of the standalone range.
            if not conditional:
                bonus += low
    return bonus


def original_base_code(row):
    if (
        row.get('name') not in REVIEWED_PROPERTIES
        or row.get('rarity') != 'set'
        or row.get('ethereal') is not False
        or type(row.get('sockets')) is not int
        or row['sockets'] != 0
        or row.get('socket_contents') != 'empty'
    ):
        return None
    definition = named_definitions().get(('set', row['name']))
    if definition is None:
        return None
    code = definition['base_code']
    tier = base_tier(code)
    props = row.get('properties', {})
    if (
        tier not in ('Normal', 'Exceptional')
        or props.get('930') not in (None, tier)
        or props.get('1216') not in (None, False)
        or props.get('738') not in (None, False)
        or row.get('base_code') not in (None, code)
    ):
        return None
    if row.get('base_code') == code:
        return code
    total = props.get('1855')
    base = equipment_base(definition['base_name'])
    bonus = _flat_bonus(definition)
    if type(total) is not int or not base or bonus is None:
        return None
    native = base[0]['details'].get('base_defense', ())
    index, _ = equipment_index(read_artifact(CATALOG))
    if len(native) != 2 or any(type(v) is not int for v in native):
        return None
    if not native[0] + bonus <= total <= native[1] + bonus:
        return None
    # Normal bases have two possible upgrades. Both must exclude this total;
    # checking only the elite tier could accidentally admit an exceptional item.
    upgrades = ('Exceptional', 'Elite') if tier == 'Normal' else ('Elite',)
    for target in upgrades:
        upgraded_code = base_at_tier(code, target)
        candidates = [item for item in index.values() if item['base_code'] == upgraded_code]
        if len(candidates) != 1:
            return None
        upgraded = candidates[0]['details'].get('base_defense', ())
        if len(upgraded) != 2 or any(type(v) is not int for v in upgraded) or native[1] >= upgraded[0]:
            return None
    return code
