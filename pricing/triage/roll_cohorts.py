"""Use supported named variant splits for roll calibration and runtime alike."""

import json

from pricing.triage.named_cohorts import compile_named, token, value


def matches_cohort(item, report):
    if item.get('ethereal') is not report['ethereal']:
        return False
    if 'coarse_facets' in report:
        if item.get('socket_contents') != 'empty':
            return False
        return all(value(item, facet, []) == expected for facet, expected in report['coarse_facets'])
    return all(item.get(key) == report.get(key) for key in ('socket_contents', 'sockets', 'base_code'))


def groups(rows):
    # Filled sockets add effects unrelated to native rolls; unknown occupancy
    # cannot establish a clean comparison even if its asks look similar.
    rows = [r for r in rows if r.get('socket_contents') == 'empty']
    if not rows:
        return []
    reference = compile_named(rows[0]['category'], rows[0]['name'], rows, [], facets=('socket_variant', 'base_code'))[0]
    result = []

    def visit(node, members, identity):
        if 'children' not in node:
            result.append((identity, members))
            return
        facet = node['facet']
        for key, child in node['children'].items():
            selected = [r for r in members if token(value(r, facet, [])) == key]
            visit(child, selected, identity | {'coarse_facets': [*identity['coarse_facets'], [facet, json.loads(key)]]})

    for eth, node in reference['named_cohorts'].items():
        visit(
            node,
            [r for r in rows if token(r.get('ethereal')) == eth],
            {'ethereal': json.loads(eth), 'coarse_facets': []},
        )
    return result
