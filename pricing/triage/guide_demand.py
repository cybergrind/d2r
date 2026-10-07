"""Compile executable guide sale recommendations into variant-specific demand."""

import json
from collections import defaultdict
from pathlib import Path


CASES = Path(__file__).with_name('guide-cases.json')


def compile_cases(cases):
    from pricing.triage.guide_cases import item_from_spec

    evidence = defaultdict(list)
    for case in cases:
        if case.get('classification') in ('context', 'pickup'):
            continue
        entries = case.get('examples')
        if entries is None:
            entries = [{'spec': s, 'expected': case.get('expected')} for s in case.get('specs', [])]
            entries += [{'item': i, 'expected': case.get('expected')} for i in case.get('items', [])]
            if case.get('spec') or case.get('item'):
                entries.append(case)
        for entry in entries:
            expected = entry.get('expected') or []
            expected = [expected] if isinstance(expected, str) else expected
            if not {'sell', 'slow'}.intersection(expected):
                continue
            item = item_from_spec(entry['spec']) if entry.get('spec') else entry.get('item')
            if not item or not item.get('category') or not item.get('name'):
                continue
            conditions = {
                k: item[k]
                for k in ('rarity', 'base_code', 'ethereal', 'sockets', 'socket_contents', 'base_ed')
                if item.get(k) is not None
            }
            record = {
                'kind': 'guide_row',
                'source': case['id'],
                'ethereal': item.get('ethereal'),
                'base_conditions': conditions,
                'properties': item.get('properties', {}),
            }
            key = item['category'] + '/' + item['name'].casefold()
            if record not in evidence[key]:
                evidence[key].append(record)
    return dict(evidence)


def merge(evidence, guides):
    merged = {key: [r for r in rows if r.get('kind') != 'guide_row'] for key, rows in evidence.items()}
    for key, rows in guides.items():
        merged.setdefault(key, []).extend(rows)
    return merged


def load():
    return compile_cases(json.loads(CASES.read_text()))


def main():
    from pricing.knowledge.refresh import atomic_json
    from pricing.triage.engine import DATA

    path = DATA / 'bands.json'
    document = json.loads(path.read_text())
    guides = load()
    document['demand'] = merge(document.get('demand', {}), guides)
    atomic_json(path, document)
    print(f'Compiled {sum(map(len, guides.values()))} variant-specific guide demand records.')


if __name__ == '__main__':
    main()
