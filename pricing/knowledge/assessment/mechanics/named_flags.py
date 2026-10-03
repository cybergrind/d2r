"""Fixed native Rest in Peace identity effect; no invented market field."""


def fixed_flag_keys(facts, definition):
    record = definition.get('game_definition', {})
    slots = [i for i in range(1, 13) if record.get(f'prop{i}') == 'rip']
    if not slots:
        return set(), []
    key = '108:0'
    row = facts.stats.get(key, {})
    if (
        len(slots) != 1
        or record.get(f'min{slots[0]}') != 1
        or record.get(f'max{slots[0]}') != 1
        or row.get('status') != 'decoded'
        or type(row.get('raw')) is not int
        or row['raw'] != 1
        or type(row.get('value')) is not int
        or row['value'] != 1
        or row.get('market_property') is not None
    ):
        return set(), [f'Named fixed flag {key} is missing, changed or unverified.']
    return {key}, []


def native_ethereal_gap(facts, definition):
    """Native indestructible precedes random ethereality; explicit ethereal wins.

    Inspect definition properties, not observed152: a socketed Zod does not
    retroactively forbid a legitimately ethereal item.
    """
    if definition.get('rarity') != 'unique':
        return None
    record = definition.get('game_definition', {})
    codes = {record.get(f'prop{i}') for i in range(1, 13)}
    if 'ethereal' in codes:
        if facts.ethereal is not True:
            return 'Native always-ethereal unique state is conflicting or unknown.'
    else:
        if 'indestruct' in codes and facts.ethereal is not False:
            return 'Native indestructible unique cannot roll ethereal; state is conflicting or unknown.'
        # Check the ORIGINAL named base: upgrades preserve pre-existing ethereality.
        base = definition.get('base_definition', {})
        if (base.get('nodurability') == 1 or base.get('durability') == 0) and facts.ethereal is not False:
            return 'Native nondurable unique cannot roll ethereal; state is conflicting or unknown.'
    return None
