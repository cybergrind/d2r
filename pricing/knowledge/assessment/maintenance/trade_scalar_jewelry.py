"""Integer boundary coverage with explicitly opted-in native compound axes."""

from pricing.knowledge.assessment.domain.facts import ItemFacts
from pricing.knowledge.assessment.maintenance import trade_base_defense, trade_compound_rolls, trade_total_defense
from pricing.knowledge.assessment.maintenance.trade_review_cases import LEGAL, REQUIRED, variant_predicate
from pricing.knowledge.assessment.policies.trade_base_defense import valid_base_defense
from pricing.knowledge.assessment.policies.trade_rolls import valid_compounds
from pricing.knowledge.assessment.policies.trade_sunder import MODE as SUNDER_MODE
from pricing.knowledge.assessment.roles.predicates import Truth, evaluate


STATES = {'candidate', 'premium', 'use_only'}
# These operations affect recipient totals, not the captured item modifiers.
PLAIN_RECIPIENT_OPERATIONS = {
    (1, 'enr'): ('energy', 8),
    (77, 'mana%'): ('item_maxmana_percent', 11),
}


def plain_item_roll(row, spec):
    if row.get('layer', 0) != 0 or any(spec.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits')):
        return False
    if spec.get('op') == 0:
        return True
    # D2MOO D2StatList.cpp: case 8 converts Energy into player mana; case 11
    # applies a percentage to player/monster totals. These reviewed item
    # modifiers remain integers. Other operated/scaled values stay rejected.
    return (
        PLAIN_RECIPIENT_OPERATIONS.get((row.get('stat_id'), row.get('property'))) == (spec.get('name'), spec.get('op'))
        and spec.get('op_param') == 0
        and spec.get('op_base') is None
    )


def specification(
    policy,
    variants,
    stat_specs,
    *,
    allowed_bases=('Ring', 'Amulet'),
    compounds=(),
    base_defense=False,
    total_defense=False,
    allow_unknown_default=False,
):
    if len(variants) != 1 or stat_specs is None:
        return None
    definition = variants[0]
    if definition.get('base_name') not in allowed_bases or any(
        definition.get(k)
        for k in (
            'native_socket_range',
            'variable_per_level_effects',
            'property_groups',
        )
    ):
        return None
    trade = policy.get('trade_qualification', {})
    total_bounds = trade_total_defense.verified_bounds(trade, definition, stat_specs) if total_defense else None
    if (total_defense and total_bounds is None) or (not total_defense and trade.get('total_defense')):
        return None
    defense_bounds = trade_base_defense.verified_bounds(trade, definition, stat_specs) if base_defense else None
    if (base_defense and defense_bounds is None) or (
        not base_defense and (definition.get('base_defense_range') or trade.get('base_defense'))
    ):
        return None
    if tuple(trade.get('compound_stats', ())) != compounds or (
        compounds and not trade_compound_rolls.verified_definition(definition, stat_specs, compounds)
    ):
        return None
    grouped = trade_compound_rolls.grouped_keys(compounds)
    bounds = dict(total_bounds) if total_bounds else {'31:0': defense_bounds} if base_defense else {}
    properties = set()
    for row in definition.get('roll_ranges', {}).values():
        low, high = row.get('min'), row.get('max')
        if type(low) is not int or type(high) is not int or low > high:
            return None
        if low == high or total_defense:
            continue
        prop = row.get('property')
        key = f'{row["stat_id"]}:{row.get("layer", 0)}'
        if not isinstance(prop, str) or not prop or (prop in properties and key not in grouped) or key in bounds:
            return None
        properties.add(prop)
        spec = stat_specs.get(str(row['stat_id']), {})
        if key not in grouped and not plain_item_roll(row, spec):
            return None
        bounds[key] = (low, high)
    if (
        not bounds
        or set(bounds) != set(trade.get('material_stats', ()))
        or len(bounds) != len(trade['material_stats'])
        or trade.get('property_choice')
        or trade.get('sunder_penalty') not in (None, SUNDER_MODE)
        or trade.get('default_status') not in (STATES | {'unresolved'} if allow_unknown_default else STATES)
        or any(b.get('status') not in STATES for b in trade.get('bands', ()))
        or policy.get('variant_rules')
    ):
        return None
    points = {key: {low, high} for key, (low, high) in bounds.items()}
    rules = [policy['valid_if'], trade['valid_if'], *(band['when'] for band in trade['bands'])]
    if not all(_collect(rule, bounds, points) for rule in rules):
        return None
    return definition, bounds, points


def _collect(rule, bounds, points):
    for group in ('all', 'any'):
        if set(rule) == {group}:
            return bool(rule[group]) and all(_collect(child, bounds, points) for child in rule[group])
    if set(rule) == {'not'}:
        return _collect(rule['not'], bounds, points)
    if variant_predicate(rule):
        return True
    if (
        set(rule) != {'op', 'key', 'value'}
        or rule['op'] != 'stat_at_least'
        or rule['key'] not in bounds
        or type(rule['value']) is not int
    ):
        return False
    key, threshold = rule['key'], rule['value']
    low, high = bounds[key]
    # Integer >= predicates partition the domain at threshold-1 / threshold.
    # threshold+1 adds no branch unless another predicate introduces it.
    # Endpoints are retained; missing/out-of-range values are tested separately.
    points[key].update(value for value in (threshold - 1, threshold) if low <= value <= high)
    return True


def _vector(item, keys, scales=None):
    values = []
    for key in keys:
        stat, parameter = map(int, key.split(':'))
        matches = [row[2] for row in item['raw_stats'] if tuple(row[:2]) == (stat, parameter)]
        if len(matches) > 1 or (matches and type(matches[0]) is not int):
            return None
        value = matches[0] if matches else None
        scale = (scales or {}).get(key, 1)
        if value is not None:
            value = value // scale if value % scale == 0 else value / scale
        values.append(value)
    return tuple(values)


def _outcome(policy, definition, item, keys, vector, *, verified_base_code=None):
    if any(value is not None and type(value) is not int for value in vector):
        return 'unresolved', None
    facts = ItemFacts(
        name=item['name'],
        base_name=item['base'],
        base_code=definition['base_code'] if verified_base_code is None else verified_base_code,
        item_type=None,
        rarity=item['rarity'],
        runeword=None,
        identified=item['identified'],
        ethereal=item['ethereal'],
        sockets=item['sockets'],
        socket_contents=item['socket_contents'],
        socket_items=(),
        gaps=(),
        capture_complete=item['complete'],
        stats={
            **{f'{s}:{p}': {'status': 'unverified', 'value': None} for s, p, _ in item['raw_stats']},
            **{
                key: {'status': 'decoded', 'value': value}
                for key, value in zip(keys, vector, strict=True)
                if value is not None
            },
        },
    )
    trade = policy['trade_qualification']
    if (
        facts.identified is not True
        or evaluate({'all': [policy['valid_if'], trade['valid_if']]}, facts).truth != Truth.TRUE
        or not valid_compounds(trade, facts)
        or not valid_base_defense(trade, facts)
    ):
        return 'unresolved', None
    for band in trade['bands']:
        truth = evaluate(band['when'], facts).truth
        if truth == Truth.UNKNOWN:
            return 'unresolved', None
        if truth == Truth.TRUE:
            return band['status'], band['reason']
    return trade['default_status'], trade['default_reason']


def case_gap(cases, policy, spec, *, reviewed_unknowns=frozenset()):
    definition, bounds, points = spec
    keys = tuple(sorted(bounds))
    maxima = tuple(bounds[key][1] for key in keys)
    compounds = tuple(policy['trade_qualification'].get('compound_stats', ()))
    required = {(LEGAL, values) for values in trade_compound_rolls.legal_vectors(keys, points, compounds)}
    required.update(
        (LEGAL, values) for values in trade_compound_rolls.mismatched_vectors(keys, maxima, bounds, compounds)
    )
    required.update((variant, maxima) for variant in REQUIRED)
    for index, key in enumerate(keys):
        for value in (None, bounds[key][0] - 1, bounds[key][1] + 1):
            values = list(maxima)
            values[index] = value
            required.add((LEGAL, tuple(values)))
    seen = set()
    contexts = set()
    total_defense = bool(policy['trade_qualification'].get('total_defense'))
    base_defense = bool(policy['trade_qualification'].get('base_defense')) or total_defense
    scales = trade_total_defense.SCALES if total_defense else {}
    for key, scale in scales.items():
        values = list(maxima)
        values[keys.index(key)] -= 1 / scale
        required.add((LEGAL, tuple(values)))
    for item, checks, variant in cases:
        vector = _vector(item, keys, scales)
        if vector is None:
            return 'Ambiguous native material roll in the executed trade case.'
        native = all(type(v) is int and bounds[k][0] <= v <= bounds[k][1] for k, v in zip(keys, vector, strict=True))
        status, reason = _outcome(policy, definition, item, keys, vector) if native else ('unresolved', None)
        context = trade_base_defense.case_context(item)
        ready = not base_defense or context == trade_base_defense.READY
        if base_defense and variant == LEGAL and vector == maxima:
            contexts.add(context)
        if (
            variant == LEGAL
            and ready
            and all(type(v) is int and bounds[k][0] <= v <= bounds[k][1] for k, v in zip(keys, vector, strict=True))
            and trade_compound_rolls.agree(keys, vector, compounds)
            and status == 'unresolved'
            and vector not in reviewed_unknowns
        ):
            return 'A legal roll branch still lacks a reviewed trade disposition.'
        if ready:
            seen.add((variant, vector))
        expected = {
            'status': status,
            **({'material_stats': policy['trade_qualification']['material_stats']} if status != 'unresolved' else {}),
        }
        labels = {'candidate': 'ordinary candidate', 'premium': 'premium candidate', 'use_only': 'use only'}
        lines = (
            []
            if status == 'unresolved'
            else [
                {
                    'text': f'Trade: {labels[status]} — {reason}',
                    'tone': 'tier_high' if status == 'premium' else 'tier_low',
                }
            ]
        )
        if checks.get('qualification') != expected or checks.get('lines') != lines:
            return 'Scalar trade verdict and rendered text/color are not explicitly asserted.'
    if not required <= seen:
        return 'Native roll limits, predicate boundaries, missing rolls or variant boundaries are not all executed.'
    if base_defense and not contexts >= trade_base_defense.REQUIRED_CONTEXTS:
        return 'Incomplete capture and additional defense contributions are not all executed.'
    return None
