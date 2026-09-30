"""Narrow source dispositions for the fixed Softcore completion contract."""

import re
from collections import defaultdict


def softcore_exclusions(inventory):
    contexts = defaultdict(list)
    for index, context in enumerate(inventory.get('variant_contexts', [])):
        name = context.get('evidence', {}).get('name')
        if (
            context.get('demand_eligibility') == 'excluded_hardcore'
            and isinstance(name, str)
            and re.match(r'^Hardcore\b', name, re.I)
            and name == context.get('variant')
            and context.get('locator', '').startswith('/')
        ):
            source = {'artifact': 'inventory', 'locator': f'/variant_contexts/{index}'}
            contexts[context.get('source_id'), context.get('build'), name].append((source, context))
    for audit_index, audit in enumerate(inventory.get('planner_slot_audits', [])):
        for profile_index, profile in enumerate(audit.get('profiles', [])):
            name = profile.get('name')
            if not (
                isinstance(name, str)
                and re.match(r'^Hardcore\b', name, re.I)
                and re.fullmatch(r'/profiles/\d+', profile.get('locator', ''))
            ):
                continue
            source = {
                'artifact': 'inventory',
                'locator': f'/planner_slot_audits/{audit_index}/profiles/{profile_index}',
            }
            context = {'source_id': audit['source_id'], 'locator': profile['locator']}
            contexts[audit['source_id'], None, name].append((source, context))
    result = {}
    for row in inventory['occurrences']:
        if row.get('source_status') != 'verified':
            continue
        candidates = list(contexts[row.get('source_id'), row.get('build'), row.get('variant')])
        if row.get('build') is not None:
            candidates.extend(contexts[row.get('source_id'), None, row.get('variant')])
        matches = [
            (source, context)
            for source, context in candidates
            if row.get('source_locator', '').startswith(context['locator'].rstrip('/') + '/')
        ]
        if len(matches) != 1:
            continue
        source, context = matches[0]
        result[row['id']] = {
            'id': row['id'],
            'state': 'excluded',
            'reason': 'Explicit Hardcore configuration is outside Softcore scope; its item identity remains in scope.',
            'source': source,
            'source_id': context['source_id'],
            'source_locator': row['source_locator'],
            'identity_id': row['identity_id'],
        }
    return result
