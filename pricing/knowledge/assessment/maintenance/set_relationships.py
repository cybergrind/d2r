"""Definition-backed set relationships for review, never independent demand votes."""

import re
from collections import defaultdict


def set_relationships(occurrences, definitions):
    sets, memberships = defaultdict(list), {}
    for definition in definitions:
        if definition.get('rarity') != 'set' or not definition.get('set_name'):
            continue
        name = definition['set_name']
        sets[name].append({'name': definition['name'], 'table_id': definition['table_id']})
        memberships[definition['name']] = name
    patterns = {name: re.compile(r'(?<!\w)' + re.escape(name) + r'(?!\w)', re.I) for name in sets}
    links = []
    for row in sorted(occurrences, key=lambda r: r['id']):
        label = row.get('original_label', '')
        membership = memberships.get(row.get('name'))
        for name in sorted(sets):
            match = patterns[name].search(label)
            if not match and membership != name:
                continue
            relation = 'piece_membership' if membership == name else 'set_reference_candidate'
            if match and re.match(r'\s+full set\b', label[match.end() :], re.I):
                relation = 'full_set_candidate'
            links.append(
                {
                    'occurrence_id': row['id'],
                    'source_id': row.get('source_id'),
                    'source_locator': row.get('source_locator'),
                    'original_label': label,
                    'set_name': name,
                    'relationship': relation,
                    'pieces': sorted(sets[name], key=lambda p: p['table_id']),
                    'required_piece_ids': None,
                    'standalone_endorsement': False,
                    'review_state': 'pending',
                }
            )
    return links
