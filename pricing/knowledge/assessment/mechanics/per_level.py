"""Verify fixed coefficients rather than compare viewer-dependent totals."""


def fixed_per_level_keys(facts, definition):
    consumed, gaps = set(), []
    for effect in definition.get('fixed_per_level_effects', ()):
        key = f'{effect["stat_id"]}:0'
        row = facts.stats.get(key, {})
        coefficient, denominator = effect['coefficient_raw'], effect['denominator']
        level = row.get('viewer_level')
        if (
            row.get('status') != 'decoded'
            or type(row.get('raw')) is not int
            or row['raw'] != coefficient
            or row.get('per_level') != {'numerator': coefficient, 'denominator': denominator}
            or type(level) is not int
            or not 1 <= level <= 99
            or type(row.get('value')) is not int
            or row['value'] != coefficient * level // denominator
        ):
            gaps.append(f'Named fixed per-level coefficient {key} is missing, changed or unverified.')
        elif row.get('market_property'):
            gaps.append(f'Named fixed per-level coefficient {key} has a viewer-dependent market projection.')
        else:
            consumed.add(key)
    return consumed, gaps


def variable_per_level_properties(facts, definition):
    properties, consumed, gaps = {}, set(), []
    for effect in definition.get('variable_per_level_effects', ()):
        key = f'{effect["stat_id"]}:0'
        row = facts.stats.get(key, {})
        raw, level = row.get('raw'), row.get('viewer_level')
        divisor = effect['denominator']
        if (
            row.get('status') != 'decoded'
            or type(raw) is not int
            or not effect['minimum_raw'] <= raw <= effect['maximum_raw']
            or raw % effect['step_raw']
            or type(level) is not int
            or not 1 <= level <= 99
            or row.get('per_level') != {'numerator': raw, 'denominator': divisor}
            or type(row.get('value')) is not int
            or row['value'] != raw * level // divisor
        ):
            gaps.append(f'Variable per-level coefficient {key} is missing or invalid.')
        elif (
            facts.runeword == 'Fortitude'
            and definition.get('name') == 'Fortitude'
            and effect
            == {'stat_id': 216, 'minimum_raw': 2048, 'maximum_raw': 3072, 'step_raw': 256, 'denominator': 2048}
        ):
            # Cached Fortitude listings use decimal-enabled field438 for the
            # coefficient (1..1.5), not the viewer's displayed life total.
            coefficient = raw / divisor
            if ('438' in facts.properties and facts.properties['438'] != coefficient) or row.get(
                'market_property'
            ) not in (None, '438'):
                gaps.append('Fortitude life-per-level market projection conflicts with its native coefficient.')
            else:
                properties['438'] = coefficient
                consumed.add(key)
        else:
            gaps.append(f'Variable per-level coefficient {key} has no reviewed market comparison.')
    return properties, consumed, gaps


def variable_per_level_gaps(facts, definition):
    return variable_per_level_properties(facts, definition)[2]
