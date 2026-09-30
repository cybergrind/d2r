"""Small, precompiled build candidates; no guide/index work in the hotkey path."""

import json
from functools import cache
from pathlib import Path


@cache
def catalog():
    return json.loads(Path(__file__).with_name('magic_targets.json').read_text())


def predicate(node, item, stats, charges, *, resolve_facts=None):
    """Three-valued matching: an unknown stat cannot satisfy a negated condition."""
    if 'all' in node or 'any' in node:
        op = 'all' if 'all' in node else 'any'
        values = [predicate(n, item, stats, charges, resolve_facts=resolve_facts) for n in node[op]]
        if op == 'all':
            return False if False in values else None if None in values else True
        return True if True in values else None if None in values else False
    if 'not' in node:
        result = predicate(node['not'], item, stats, charges, resolve_facts=resolve_facts)
        return None if result is None else not result
    op = node['op']
    if op == 'fact_eq':
        value = item.get(node['field'])
        return None if value is None else value == node['value']
    if op == 'charge_skill':
        return node['skill_id'] in charges
    if op == 'stat_at_least':
        key = tuple(map(int, node['key'].split(':')))
        value = stats.get(key, 0)
        return None if value is None else value >= node['value']
    # Socket payload/innate/affix rules use the same evidence semantics as Alt-D.
    # Resolve lazily: ordinary shop stat matching needs no assessment projection.
    from pricing.knowledge.assessment.roles.predicates import Truth, evaluate, validate

    validate(node)
    if resolve_facts is None:
        return None
    return {Truth.TRUE: True, Truth.FALSE: False}.get(evaluate(node, resolve_facts()).truth)


@cache
def by_type():
    result = {}
    for target in sorted(catalog()['targets'], key=lambda t: (not t['id'].startswith('named:'), t['id'])):
        for kind in target['types']:
            result.setdefault(kind, []).append(target)
    return result


def match_catalog(observation, stats):
    item = observation['item']
    if item.get('rarity') != 'magic' or item.get('identified') is not True:
        return []
    stats = dict(stats)
    for stat in observation.get('unresolved_stats', []):
        stats[stat['id'], stat['layer']] = None
    charges = {
        row['memory_stat']['layer'] >> 6
        for row in observation.get('decoded_stats', [])
        if row.get('status') == 'decoded'
        and row.get('memory_stat', {}).get('id') == 204
        and row.get('charges', {}).get('maximum', 0) > 0
    }

    @cache
    def resolve_facts():
        from pricing.knowledge.assessment.adapters.capture import normalize

        return normalize(observation)

    hits = []
    for target in by_type().get(item['item_type'], []):
        if target.get('base_codes') and item.get('base_code') not in target['base_codes']:
            continue
        if predicate(target['must'], item, stats, charges, resolve_facts=resolve_facts) is True:
            hits.append(target['label'])
    return list(dict.fromkeys(hits))
