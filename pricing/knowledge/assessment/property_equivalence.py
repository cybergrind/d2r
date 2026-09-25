"""Lossless market-property representations; no roll tolerance or price grouping."""

import math


# Verified against the cached appraisal-properties catalog, 2026-09-24.
ALL_RESISTANCES = '441'
ELEMENTAL_RESISTANCES = frozenset({'427', '428', '426', '401'})
ALL_ATTRIBUTES = '727'
ATTRIBUTES = frozenset({'437', '429', '582', '421'})
BOOLEAN_FLAGS = {'591': 'Cannot Be Frozen', '432': 'Indestructible'}


def validate_finite_properties(properties):
    for key, value in properties.items():
        if type(value) in (int, float) and not math.isfinite(value):
            raise ValueError(f'Market property {key} must be finite.')


def canonical_properties(properties):
    validate_finite_properties(properties)
    result = dict(properties)
    # Verified market booleans correspond to exact decoded native flag values.
    # Do not coerce other properties or truthy/non-boolean payloads.
    for key, label in BOOLEAN_FLAGS.items():
        if key not in result:
            continue
        value = result[key]
        if type(value) not in (bool, int) or value not in (0, 1):
            raise ValueError(f'{label} must be a verified boolean flag.')
        result[key] = int(value)
    for combined, components, label in (
        (ALL_RESISTANCES, ELEMENTAL_RESISTANCES, 'Resistance'),
        (ALL_ATTRIBUTES, ATTRIBUTES, 'Attribute'),
    ):
        for key in (components | {combined}) & result.keys():
            value = result[key]
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f'{label} values must be finite numbers.')
        if combined in result:
            if components & result.keys():
                raise ValueError(
                    f'Combined and individual {label.lower()} values have ambiguous contribution semantics.'
                )
            value = result.pop(combined)
            result.update(dict.fromkeys(components, value))
    return result
