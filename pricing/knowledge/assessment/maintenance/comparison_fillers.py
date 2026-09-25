"""Compile reviewed fixed comparison fillers from recipient-specific game data."""

ATTRIBUTE_RUNES = ('Fal Rune', 'Lum Rune', 'Ko Rune', 'Io Rune')
DEFENSIVE_RUNES = ('Um Rune', 'Shael Rune', 'Ber Rune', 'Cham Rune', 'Zod Rune')
RESIST_RUNES = ('Ral Rune', 'Ort Rune', 'Thul Rune', 'Tal Rune')


def grades(kind):
    return (f'Chipped {kind}', f'Flawed {kind}', kind, f'Flawless {kind}', f'Perfect {kind}')


ARMOR = (
    *ATTRIBUTE_RUNES,
    *DEFENSIVE_RUNES,
    *RESIST_RUNES,
    'Perfect Topaz',
    'Ist Rune',
    'Lem Rune',
    *grades('Ruby'),
    *grades('Emerald'),
    *grades('Amethyst'),
)
REVIEWED = {
    'helm': ARMOR,
    'armor': ARMOR,
    'shield': (*ATTRIBUTE_RUNES, *DEFENSIVE_RUNES, *RESIST_RUNES, 'Ist Rune', 'Lem Rune', *grades('Diamond')),
    'weapon': (*ATTRIBUTE_RUNES, 'Zod Rune', 'Shael Rune', 'Ber Rune', 'Um Rune', 'Ist Rune', 'Lem Rune'),
}
# Comparison code handles direct integer values plus fixed-point maxhp7 and flags152/153.
SUPPORTED_STATS = frozenset({0, 1, 2, 3, 7, 36, 39, 41, 43, 45, 79, 80, 93, 99, 102, 135, 136, 152, 153})


def compile_fillers(gems, properties, stats, reviewed=REVIEWED):
    by_name = {row['name']: row for row in gems.values()}
    if len(by_name) != len(gems):
        raise ValueError('Duplicate socket filler name')
    stat_ids = {row['name']: int(key) for key, row in stats.items()}
    compiled = {}
    for family, names in reviewed.items():
        if family not in ('helm', 'armor', 'shield', 'weapon') or len(set(names)) != len(names):
            raise ValueError('Invalid socket recipient or duplicate reviewed filler')
        prefix = 'helm' if family == 'armor' else family
        entries = {}
        for name in names:
            gem = by_name.get(name)
            if gem is None:
                raise ValueError(f'Missing reviewed socket filler: {name}')
            effects = {}
            for slot in range(1, 4):
                field = f'{prefix}Mod{slot}'
                code = gem.get(field + 'Code')
                if not code:
                    continue
                low, high = gem.get(field + 'Min'), gem.get(field + 'Max')
                if type(low) is not int or low != high or gem.get(field + 'Param', 0) != 0:
                    raise ValueError(f'Nonfixed socket effect: {name}/{code}')
                spec = properties.get(code)
                if spec is None:
                    raise ValueError(f'Unknown socket property: {code}')
                previous_count = len(effects)
                for part in range(1, 8):
                    function = spec.get(f'func{part}')
                    if not function:
                        continue
                    if code == 'indestruct' and function == 20 and low == 1:
                        stat = 152
                    elif function in (1, 3, 8):
                        stat = stat_ids.get(spec.get(f'stat{part}'))
                    else:
                        raise ValueError(f'Unreviewed socket function: {code}/{function}')
                    if stat not in SUPPORTED_STATS or str(stat) in effects:
                        raise ValueError(f'Unsupported or repeated socket stat: {stat}')
                    effects[str(stat)] = low
                if len(effects) == previous_count:
                    raise ValueError(f'Empty socket property: {name}/{code}')
            if not effects:
                raise ValueError(f'Empty socket effect: {name}/{family}')
            entries[name] = effects
        compiled[family] = entries
    return compiled
