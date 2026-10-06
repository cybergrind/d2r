"""Import documented plain/life skiller patterns; historical prices are not bands."""

import json
import re

from pricing.knowledge.refresh import atomic_json
from pricing.triage.build import ROOT
from pricing.triage.charm_modifiers import TREES


SOURCE = 'pricing/data/wp-h-jewels-charms.json'
# Explicit paid plain variants in primer §4.1; not every listed tree qualifies.
# In particular, WP-H's '-plain' buckets can contain gold-find/FHR suffixes.
PAID_PLAIN = frozenset(
    {
        'CH-skiller-pala-combat',
        'CH-skiller-sorc-lightning',
        'CH-skiller-ama-javelin',
        'CH-skiller-sorc-cold',
        'CH-skiller-sorc-fire',
        'CH-skiller-necro-pnb',
        'CH-skiller-druid-elemental',
        'CH-skiller-assa-martial-arts',
    }
)


def observed_rule(key, prop, source):
    return {
        'category': 'magic',
        'name': 'Grand Charm',
        'bucket': key + '-observed-suffix',
        'properties': {prop: 1},
        'band_facets': ['charm_suffix'],
        'compare_property': '418',
        'compare_label': 'life',
        'compare_range': {'min': 1, 'max': 45},
        'source': source,
        'imported_skiller': key,
    }


def compile_skillers(document):
    rules = []
    observed = set()
    for key, row in document.items():
        if not isinstance(row, dict) or row.get('class') != 'charm-grand-skiller':
            continue
        match = re.search(r'\(prop (\d+)\)', row.get('bucket_def', ''))
        life = row.get('split', {}).get(key + '-life', {})
        if not match:
            continue
        rules.append(observed_rule(key, match[1], SOURCE + '#' + key))
        observed.add(match[1])
        if key in PAID_PLAIN:
            rules.append(
                {
                    'category': 'magic',
                    'name': 'Grand Charm',
                    'properties': {match[1]: 1},
                    'conditions': {'charm_suffix': {'in': [{}]}},
                    'pattern': {'properties': {match[1]: 1}},
                    'pattern_label': 'Documented plain skill-tree charm',
                    'source': 'guides/pricing-primer.html#s4-1',
                    'imported_skiller': key,
                }
            )
        if life.get('n_priced', 0) < 1:
            continue
        properties = {match[1]: 1, '418': {'min': 1, 'max': 45}}
        rules.append(
            {
                'category': 'magic',
                'name': 'Grand Charm',
                'bucket': key + '-life',
                'properties': properties,
                'band_facets': ['charm_suffix'],
                'pattern': {'properties': properties},
                'pattern_label': 'Documented skill-tree + life combination',
                'labels': {match[1]: 'skill tree', '418': 'life'},
                'source': SOURCE + '#' + key + '/split/' + key + '-life',
                'imported_skiller': key,
            }
        )
    # Historical research omitted some trees. Enable exact observed comparisons,
    # without treating catalog presence as evidence of a paid plain/life pattern.
    for prop in sorted(TREES - observed):
        rules.append(
            observed_rule(
                'CH-skiller-native-' + prop, prop, 'pricing/data/appraisal-properties.json#/properties/' + prop
            )
        )
    return rules


def main():
    path = ROOT / 'pricing/data/triage/rules.json'
    document = json.loads(path.read_text())
    rules = compile_skillers(json.loads((ROOT / SOURCE).read_text()))
    document['rows'] = [r for r in document['rows'] if not r.get('imported_skiller')] + rules
    atomic_json(path, document)
    print(
        json.dumps(
            {
                'skiller_rows': len(rules),
                'life_patterns': sum('418' in r.get('pattern', {}).get('properties', {}) for r in rules),
                'plain_patterns': sum(r.get('pattern_label') == 'Documented plain skill-tree charm' for r in rules),
                'historical_prices_imported': False,
            }
        )
    )


if __name__ == '__main__':
    main()
