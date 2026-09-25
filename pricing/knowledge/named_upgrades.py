"""Pure ascending named-item upgrade metadata shared by build and validation."""


def named_upgrade_variants(entry, bases):
    """Compile mutually verified ascending chains for the standalone reader."""
    fields = ('normcode', 'ubercode', 'ultracode')
    original = entry['base_code']
    chain = tuple(bases.get(original, {}).get(field) for field in fields)
    if not all(isinstance(code, str) and code for code in chain) or len(set(chain)) != 3 or original not in chain:
        return {}
    variants = {}
    for code in chain[chain.index(original) + 1 :]:
        target = bases.get(code, {})
        if tuple(target.get(field) for field in fields) != chain:
            continue
        defense = entry.get('base_defense_range')
        variants[code] = {
            'base_defense_range': (
                {**defense, 'min': target['minac'], 'max': target['maxac']}
                if defense and type(target.get('minac')) is int and type(target.get('maxac')) is int
                else None
            ),
        }
    return variants
