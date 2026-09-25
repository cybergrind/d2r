"""Compile supported compound rune effects without collapsing their native units."""

DESTINATIONS = {'weapon': 'weapon', 'shield': 'shield', 'armor': 'helm', 'helm': 'helm'}
FUNCTIONS = {
    'dmg-pois': ('poison', ((15, 'poisonmindam'), (16, 'poisonmaxdam'), (17, 'poisonlength'))),
    'dmg-cold': ('cold', ((15, 'coldmindam'), (16, 'coldmaxdam'), (17, 'coldlength'))),
    'dmg-fire': ('fire', ((15, 'firemindam'), (16, 'firemaxdam'))),
    'dmg-ltng': ('lightning', ((15, 'lightmindam'), (16, 'lightmaxdam'))),
}


def socket_compound_effects(runes, gems, properties):
    """Retain individual elemental sources; this is not a complete modifier inventory."""
    result = {family: [] for family in DESTINATIONS}
    if any(code not in gems for code in runes):
        return result
    for family, prefix in DESTINATIONS.items():
        for code in runes:
            for slot in range(1, 4):
                stem = f'{prefix}Mod{slot}'
                gem = gems[code]
                property_code = gem.get(stem + 'Code')
                physical = {'dmg-min': (5, 159), 'dmg-max': (6, 160)}.get(property_code)
                if physical and family == 'weapon':
                    low, high = gem.get(stem + 'Min'), gem.get(stem + 'Max')
                    if (
                        properties.get(property_code, {}).get('func1') == physical[0]
                        and type(low) is int
                        and type(high) is int
                        and low == high
                        and low > 0
                    ):
                        result[family].append(
                            {
                                'kind': 'physical_mirror',
                                'rune': code,
                                'slot': slot,
                                'stat_id': physical[1],
                                'value': low,
                            }
                        )
                    continue
                if property_code not in FUNCTIONS:
                    continue
                kind, functions = FUNCTIONS[property_code]
                spec = properties.get(property_code, {})
                if any((spec.get(f'func{i}'), spec.get(f'stat{i}')) != pair for i, pair in enumerate(functions, 1)):
                    continue
                low, high, frames = (gem.get(stem + key) for key in ('Min', 'Max', 'Param'))
                values = (low, high, frames) if kind in ('poison', 'cold') else (low, high)
                if any(type(v) is not int or v <= 0 for v in values) or low > high:
                    continue
                if kind != 'poison':
                    result[family].append(
                        {
                            'kind': kind,
                            'rune': code,
                            'slot': slot,
                            'minimum_damage': low,
                            'maximum_damage': high,
                            **({'duration_frames': frames} if kind == 'cold' else {}),
                        }
                    )
                    continue
                result[family].append(
                    {
                        'kind': 'poison',
                        'rune': code,
                        'slot': slot,
                        'minimum_rate_raw': low,
                        'maximum_rate_raw': high,
                        'duration_frames': frames,
                        'source_count': 1,
                    }
                )
    return result
