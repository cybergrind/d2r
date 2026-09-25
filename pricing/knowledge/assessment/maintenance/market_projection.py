"""Compile exact skill-family market labels from offline metadata, never tooltip text."""

import hashlib
import json
from pathlib import Path

from inventory_tracking.items.stat_constants import CLASS_NAMES, SKILL_TABS
from inventory_tracking.items.stats import StatContext, decode_stat


ROOT = Path(__file__).resolve().parents[4]
OUTPUT = Path(__file__).resolve().parents[1] / 'rules/native_market_properties.json'
PROBE = 104729
# Explicit reviewed wording difference; same class-wide skill stat, not a skill tab.
LABEL_ALIASES = {'83:7': '+{{value}} to Warlock Skills'}


def compile_projection(metadata, properties):
    labels = {}
    for key, prop in properties.items():
        if prop.get('types') != ['number']:
            continue
        for label in prop.get('labels', []):
            labels.setdefault(label, set()).add(key)
    candidates = [(83, cls) for cls in range(len(CLASS_NAMES))]
    candidates += [(188, cls * 8 + tree) for cls in range(len(SKILL_TABS)) for tree in range(3)]
    candidates += [(stat, int(skill)) for stat in (97, 107, 151) for skill in metadata['skills']]
    mappings, unmapped = {}, {}
    for stat, layer in candidates:
        key = f'{stat}:{layer}'
        fields = decode_stat(
            StatContext(
                {'id': stat, 'layer': layer, 'raw': PROBE},
                metadata['stats'].get(str(stat), {}),
                metadata['skills'],
                None,
            )
        )
        if not fields:
            continue
        native_label = fields['text'].replace(str(PROBE), '{{value}}')
        label = LABEL_ALIASES.get(key, native_label)
        matches = labels.get(label, set())
        if len(matches) == 1:
            mappings[key] = {'property_id': next(iter(matches)), 'label': label, 'native_label': native_label}
        else:
            unmapped[key] = {'label': label, 'reason': 'ambiguous market label' if matches else 'no exact market label'}
    return {'schema_version': 1, 'mappings': mappings, 'unmapped': unmapped}


def main():
    inputs = ['inventory_tracking/items/data/item_metadata.json', 'pricing/data/appraisal-properties.json']
    payloads = [(ROOT / path).read_bytes() for path in inputs]
    document = compile_projection(json.loads(payloads[0]), json.loads(payloads[1])['properties'])
    document['inputs'] = {path: hashlib.sha256(raw).hexdigest() for path, raw in zip(inputs, payloads, strict=True)}
    document['review'] = '2026-09-24: Scalar skill families; exact labels plus reviewed Warlock class wording alias.'
    temporary = OUTPUT.with_suffix('.tmp')
    temporary.write_text(json.dumps(document, indent=2) + '\n')
    temporary.replace(OUTPUT)
    print(json.dumps({'mapped': len(document['mappings']), 'unmapped': len(document['unmapped'])}))


if __name__ == '__main__':
    main()
