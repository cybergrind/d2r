"""Join recommended bases to current endgame runeword demand, without pricing them."""

import re
from collections import defaultdict

from inventory_tracking.items.metadata import metadata


def explicit_bases(demand, bases):
    """Resolve unambiguous equipment names in reviewed variant labels."""
    patterns = [
        (base['code'], re.compile(r'(?<!\w)' + re.escape(base['name']) + r'(?!\w)', re.I))
        for base in bases.values()
        if base['category'] in ('weapons', 'armor')
    ]
    result = {}
    for key, records in demand.items():
        if not key.startswith('runewords/'):
            continue
        for record in records:
            label = record.get('original_label', '')
            if not record.get('build') or label in result:
                continue
            matches = [code for code, pattern in patterns if pattern.search(label)]
            result[label] = matches[0] if len(matches) == 1 else None
    return result


def compile_bases(recommendations, utility, demand):
    game = metadata()
    bases = {base['code']: base for base in game['bases'].values()}
    explicit = explicit_bases(demand, bases)
    result = defaultdict(list)
    for row in utility:
        details = row.get('details', {})
        if details.get('legality') != 'verified_type_and_capacity':
            continue
        base = bases.get(row.get('base_code'))
        if not base or base['type'] in game['staffmods']['classes_by_type']:
            continue
        word = details['runeword']
        recommended = recommendations.get(base['name'], {})
        shortlisted = recommended.get('sockets_by_runeword', {}).get(word) == row['sockets']
        for record in demand.get('runewords/' + word.casefold(), []):
            if not record.get('build'):
                continue
            declared = explicit.get(record.get('original_label', '')) == base['code']
            if not (shortlisted or declared):
                continue
            preferred = recommended.get('eth_wanted')
            ethereal = record.get('ethereal')
            if ethereal is None:
                if type(preferred) is bool:
                    ethereal = preferred
                elif not declared:
                    ethereal = record.get('side') == 'merc'
            entry = record | {
                'kind': 'recommended_runeword_base',
                'runeword': word,
                'ethereal': ethereal,
                'base_source': record['source'] if declared else 'pricing/data/wp-a-bases.json',
                'base_source_date': recommended.get('date'),
                'mechanics_source': row.get('source_locator'),
                'base_conditions': {
                    'base_code': base['code'],
                    'rarity': {'in': ['normal', 'superior']},
                    'sockets': row['sockets'],
                    'socket_contents': 'empty',
                },
            }
            key = 'base/' + base['name'].casefold()
            if entry not in result[key]:
                result[key].append(entry)
    return dict(result)
