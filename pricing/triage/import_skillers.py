"""Import documented life-skiller patterns; old aggregate prices are not bands."""

import json
import re

from pricing.knowledge.refresh import atomic_json
from pricing.triage.build import ROOT


SOURCE = 'pricing/data/wp-h-jewels-charms.json'


def compile_skillers(document):
    rules = []
    for key, row in document.items():
        if not isinstance(row, dict) or row.get('class') != 'charm-grand-skiller':
            continue
        match = re.search(r'\(prop (\d+)\)', row.get('bucket_def', ''))
        life = row.get('split', {}).get(key + '-life', {})
        if not match:
            continue
        rules.append(
            {
                'category': 'magic',
                'name': 'Grand Charm',
                'bucket': key + '-observed-suffix',
                'properties': {match[1]: 1},
                'band_facets': ['charm_suffix'],
                'compare_property': '418',
                'compare_label': 'life',
                'compare_range': {'min': 1, 'max': 45},
                'source': SOURCE + '#' + key,
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
                'life_patterns': sum('pattern' in r for r in rules),
                'historical_prices_imported': False,
            }
        )
    )


if __name__ == '__main__':
    main()
