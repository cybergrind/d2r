"""Transcribe the existing 50 charm/jewel watches into pattern and roll tables."""

import json
from pathlib import Path

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.adapters.market_projection import market_properties


ROOT = Path(__file__).resolve().parents[2]


def compile_watches(rows):
    stats = metadata()['stats']
    mapping = {f'{key}:0': row['property_id'] for key, row in stats.items() if row.get('property_id')}
    mapping.update(market_properties())
    mapping.update({'17:0': '510', '18:0': '510'})  # combined enhanced damage, equal native halves
    resistance_ids = {stats[key]['property_id'] for key in ('39', '41', '43', '45')}
    compiled = []
    for row in rows:
        if row.get('kind') != 'affixed_value_watch':
            continue
        details = row['details']
        properties, labels = {}, {}
        for native, bounds in details['native_conditions'].items():
            if native == '59:0':
                continue  # Poison watches below use their tooltip damage, never duration alone.
            prop = mapping[native]
            if prop in properties and properties[prop] != bounds:
                raise ValueError(f'Conflicting combined stat in {details["watch_id"]}')
            if bounds.get('min') == 0:
                continue  # Added life cannot reduce the value of a paid plain-resistance charm.
            properties[prop] = bounds
            label = stats.get(native.split(':')[0], {}).get('label') or native
            labels[prop] = label.replace('{{value}}', '').strip('+ %').strip()
        if details['watch_id'] == 'pestilent-life':
            properties['518'] = {'min': 175}
            labels['518'] = 'poison damage'
        elif details['watch_id'] == 'pestilent-anthrax':
            properties['518'] = {'min': 313}
            labels['518'] = 'poison damage'
        if '448' in labels:
            labels['448'] = 'max damage'
        # Zero-inclusive life is an exclusion for plain resistance charms, not a paid stat.
        required = {
            p: ({'max': -1} if b.get('max', 0) < 0 else {'min': 1}) for p, b in properties.items() if b.get('min') != 0
        }
        # Four equal resistances constitute one affix, not a four-stat combination.
        components = set(required) - resistance_ids
        resistance = any(p in required for p in resistance_ids)
        rule = {
            'category': 'magic',
            'name': row['name'],
            'bucket': details['watch_id'],
            'properties': properties,
            'labels': labels,
            'premium': details.get('guide_tier') in ('High', 'Very High'),
            'pattern_label': details['roll_bucket'] + ' pattern complete',
            'source': row['source'],
            'imported_watch': details['watch_id'],
        }
        if len(components) + resistance > 1:
            rule['pattern'] = {'properties': required}
        elif not rule['premium']:
            # A documented single-affix watch still warrants review at its
            # stated roll, but neither its priority nor weaker rolls prove a sale.
            rule['pattern'] = {'properties': properties}
        compiled.append(rule)
    return compiled


def main():
    source = json.loads((ROOT / 'pricing/data/appraisal-value-watch.json').read_text())
    path = ROOT / 'pricing/data/triage/rules.json'
    doc = json.loads(path.read_text())
    rows = compile_watches(source['rows'])
    doc['rows'] = [r for r in doc['rows'] if 'imported_watch' not in r] + rows
    path.write_text(json.dumps(doc, indent=2) + '\n')
    print(f'Imported {len(rows)} charm/jewel rules')


if __name__ == '__main__':
    main()
