"""Independent completeness check for every native facet roll/event branch."""

from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance import trade_scalar_jewelry
from pricing.knowledge.assessment.maintenance.trade_review_cases import LEGAL
from pricing.knowledge.assessment.policies.trade_facets import definition_for_review


def specification(policy, variants, stat_specs):
    if (policy.get('quality'), policy.get('name')) != ('unique', 'Rainbow Facet') or policy.get('trade_qualification'):
        return None
    definitions = {d['table_id']: d for d in variants}
    if len(definitions) != 8 or len(policy.get('variant_rules', [])) != 8:
        return None
    specs = {}
    for variant in policy['variant_rules']:
        trade = variant.get('trade_qualification', {})
        table = trade.get('facet_table_id')
        if variant['table_ids'] != [table] or table not in definitions or table in specs:
            return None
        try:
            definition = definition_for_review(trade)
        except ValueError, KeyError, TypeError:
            return None
        if thaw(definitions[table]) != thaw(definition):
            return None
        effective = {k: v for k, v in policy.items() if k != 'variant_rules'}
        effective.update(trade_qualification=trade, valid_if={'all': [policy['valid_if'], variant['valid_if']]})
        scalar = trade_scalar_jewelry.specification(effective, [definition], stat_specs, allowed_bases=('Jewel',))
        if scalar is None:
            return None
        specs[table] = (effective, scalar)
    return {'definition': variants[0], 'native_specs': specs}


def _trigger(item, definition):
    # Independent native event fields; no runtime trigger helper supplies the verdict.
    game = definition['game_definition']
    names = {
        'Chain Lightning': 53,
        'Blizzard': 59,
        'Meteor': 56,
        'Poison Nova': 92,
        'Nova': 48,
        'Frost Nova': 44,
        'Blaze': 46,
        'Venom': 278,
    }
    event = 197 if game['prop4'] == 'death-skill' else 199
    expected = (event, names[game['par4']] * 64 + game['max4'], 100)
    triggers = [tuple(row) for row in item['raw_stats'] if row[0] in (197, 199)]
    if triggers == [expected]:
        return 'verified'
    if not triggers:
        return 'missing'
    if len(triggers) == 1 and triggers[0][:2] == expected[:2]:
        return 'chance'
    return 'identity'


def case_gap(cases, policy, spec):
    grouped = {table: [] for table in spec['native_specs']}
    bad_triggers = {table: set() for table in grouped}
    for item, checks, signature in cases:
        table = item.get('named_table_id')
        if table not in grouped:
            return 'Facet trade case lacks a reviewed native variant.'
        effective, scalar = spec['native_specs'][table]
        trigger = _trigger(item, scalar[0])
        if trigger == 'verified':
            grouped[table].append((item, checks, signature))
            continue
        if checks.get('qualification') != {'status': 'unresolved'} or checks.get('lines') != []:
            return 'Unverified facet trigger must not receive trade credit.'
        if signature == LEGAL:
            keys = tuple(sorted(scalar[1]))
            vector = trade_scalar_jewelry._vector(item, keys)
            if vector == tuple(scalar[1][k][1] for k in keys):
                bad_triggers[table].add(trigger)
    for table, (effective, scalar) in spec['native_specs'].items():
        if bad_triggers[table] != {'missing', 'chance', 'identity'}:
            return 'Missing, conflicting and cross-variant facet triggers are not all executed.'
        if gap := trade_scalar_jewelry.case_gap(grouped[table], effective, scalar):
            return gap
    return None
