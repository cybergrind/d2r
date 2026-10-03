"""Prove absent percent damage from captured magic/rare affix identities.

An empty local stat list cannot prove absence: some historical runeword captures
omit known ED. This proof instead checks every selected prefix/suffix/automod and
requires empty sockets. Unknown properties and crafted fixed bonuses stay open.
"""

from collections.abc import Mapping

from inventory_tracking.items.metadata import metadata


# Native property functions 1/3/8/10/19 write their designated stats. All slots
# of these properties were checked against properties.json; none writes local
# or per-level percent damage. Poison additionally writes poison_count only.
# Review: appraisal-affix-non-ed-native-functions-2026-10-02.json. Keep a positive
# list: an unknown property must never establish absence of enhanced damage.
NON_DAMAGE_PROPERTIES = frozenset(
    [
        'abs-cold',
        'abs-fire',
        'abs-ltng',
        'ac',
        'att',
        'att%',
        'att-demon',
        'att-undead',
        'balance1',
        'balance2',
        'balance3',
        'block',
        'block2',
        'cast1',
        'cast3',
        'charged',
        'cold-len',
        'cold-max',
        'cold-min',
        'dex',
        'dmg-ac',
        'dmg-demon',
        'dmg-to-mana',
        'dmg-undead',
        'ease',
        'enr',
        'fire-max',
        'fire-min',
        'gold%',
        'half-freeze',
        'howl',
        'hp',
        'ignore-ac',
        'knock',
        'lifesteal',
        'light',
        'ltng-max',
        'ltng-min',
        'mag%',
        'mana',
        'mana-kill',
        'manasteal',
        'move1',
        'move2',
        'move3',
        'noheal',
        'pierce-cold',
        'pierce-dmg',
        'pierce-fire',
        'pierce-ltng',
        'pierce-mag',
        'pierce-pois',
        'pois-len',
        'pois-max',
        'pois-min',
        'red-dmg',
        'red-mag',
        'regen',
        'regen-stam',
        'res-all',
        'res-cold',
        'res-fire',
        'res-ltng',
        'res-pois',
        'res-pois-len',
        'skilltab',
        'stack',
        'stam',
        'stamdrain',
        'str',
        'swing1',
        'swing2',
        'swing3',
        'thorns',
    ]
)


def affixed_without_ed(facts):
    if (
        facts.rarity not in ('magic', 'rare')
        or facts.runeword
        or not facts.capture_complete
        or facts.identified is not True
        or facts.socket_contents != 'empty'
        or facts.socket_items
        or {'17:0', '18:0'} & facts.stats.keys()
        or facts.properties.get('510') not in (None, 0)
    ):
        return False
    affixes = facts.native_affixes
    if not isinstance(affixes, Mapping) or set(affixes) != {'prefix', 'suffix', 'auto'}:
        return False
    if affixes != facts.provenance.get('capture', {}).get('native_affixes'):
        return False
    count = 0
    for table, ids in affixes.items():
        limit = 1 if table == 'auto' or facts.rarity == 'magic' else 3
        if not isinstance(ids, (list, tuple)) or len(ids) > limit:
            return False
        if any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
            return False
        for index in ids:
            entry = metadata()['affixes'][table].get(str(index), {})
            if (
                entry.get('table_id') != index
                or entry.get('affix_table') != table
                or facts.base_code not in entry.get('base_codes', [])
                or (facts.rarity == 'rare' and not entry.get('rare'))
                or any(r.get('stat_id') in (17, 18) for r in entry.get('roll_ranges', {}).values())
            ):
                return False
            native = entry.get('game_definition', {})
            codes = [v for k, v in native.items() if k.startswith('mod') and k.endswith('code') and v]
            if not codes or any(code not in NON_DAMAGE_PROPERTIES for code in codes):
                return False
            count += 1
    return count > 0
