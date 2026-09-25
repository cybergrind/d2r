"""Compile only reviewed additive socket scalars; unknown property functions fail closed."""

from pricing.knowledge.assessment.mechanics.intrinsic_socket_rolls import SUPPORTED


# D2MOO ItemMods: 5/6 physical min/max, 7 enhanced damage, 20 indestructible.
IMPLICIT_STATS = {5: {21, 23, 159}, 6: {22, 24, 160}, 7: {17, 18}, 20: {152}}
EXPLICIT_FUNCTIONS = {1, 2, 3, 8, 15, 16, 17}


def compile_scalars(gems, properties, stats, bases):
    target_names = {stats[key.split(':')[0]]['name']: key for key in SUPPORTED}
    effects = {}
    for code, gem in gems.items():
        destinations = {}
        for destination in ('weapon', 'helm', 'shield'):
            totals = dict.fromkeys(SUPPORTED, 0)
            for slot in range(1, 4):
                prefix = f'{destination}Mod{slot}'
                prop = gem.get(prefix + 'Code')
                if not prop:
                    continue
                spec = properties[prop]
                for part in range(1, 8):
                    function = spec.get(f'func{part}')
                    if not function:
                        continue
                    if function in IMPLICIT_STATS:
                        if IMPLICIT_STATS[function] & {int(k.split(':')[0]) for k in SUPPORTED}:
                            raise ValueError('Implicit socket stat needs explicit reviewed support')
                        continue
                    if function not in EXPLICIT_FUNCTIONS or not spec.get(f'stat{part}'):
                        raise ValueError(f'Unreviewed socket property function: {prop}/{function}')
                    key = target_names.get(spec[f'stat{part}'])
                    if key is None:
                        continue
                    low, high = gem.get(prefix + 'Min'), gem.get(prefix + 'Max')
                    if function != 1 or type(low) is not int or low != high or gem.get(prefix + 'Param', 0) != 0:
                        raise ValueError(f'Socket scalar is not fixed and direct: {prop}')
                    totals[key] += low
            destinations[destination] = totals
        effects[code] = destinations
    return {
        'effects': effects,
        'recipients': {
            code: {0: 'weapon', 1: 'helm', 2: 'shield'}[base['gemapplytype']]
            for code, base in bases.items()
            if base.get('gemapplytype') in (0, 1, 2)
        },
    }
