"""Offline census of saved item payloads and bundled roll endpoints; never reads a process."""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from inventory_tracking.items.metadata import decode_stats, item_base, metadata, metadata_generation


def item_rows(value):
    if isinstance(value, dict):
        if 'resource_stats' in value and 'txt_id' in value:
            yield value
        for child in value.values():
            yield from item_rows(child)
    elif isinstance(value, list):
        for child in value:
            yield from item_rows(child)


def property_references(root):
    """Direct native-stat references; implicit property functions are not covered."""
    properties = json.loads((root / 'properties.json').read_text())
    references = defaultdict(list)
    for table in ('uniqueitems', 'setitems', 'sets', 'magicprefix', 'magicsuffix', 'runes', 'gems', 'automagic'):
        path = root / (table + '.json')
        for key, row in json.loads(path.read_text()).items():
            if table in ('magicprefix', 'magicsuffix', 'automagic') and (
                not row.get('spawnable') or not row.get('frequency') or row.get('version') == 0
            ):
                continue
            if table in ('uniqueitems', 'setitems') and not row.get('spawnable'):
                continue
            if table == 'runes' and not row.get('complete'):
                continue
            for field, code in row.items():
                if not isinstance(code, str) or code not in properties or not re.search(r'prop|code', field, re.I):
                    continue
                for stat_field, name in properties[code].items():
                    if re.fullmatch(r'stat[1-7]', stat_field):
                        references[name].append(
                            {
                                'source': str(path),
                                'row': key,
                                'field': field,
                                'property': code,
                            }
                        )
    return references


def audit(paths, *, sources=None):
    catalog = metadata()
    evidence = defaultdict(Counter)
    failures, errors, seen = [], [], set()
    file_count = 0

    def check(stats, source, kind, base=None):
        # This is an encoding audit at a fixed reference level, not a replay of
        # the original viewer's level-dependent tooltip or appraisal verdict.
        _, _, unresolved = decode_stats(stats, base=base, viewer_level=91)
        for stat in stats:
            evidence[str(stat['id'])][kind] += 1
        if unresolved:
            failures.append({'source': source, 'stats': unresolved})

    for path in paths:
        file_count += 1
        try:
            document = json.loads(path.read_text())
            for row in item_rows(document):
                arrays = row['resource_stats']
                for array in arrays.get('arrays', []):
                    if array.get('header_offset') != 0xE8:
                        continue
                    stats = list(array['stats'])
                    for field, ids in (('damage_modifiers', (17, 18)), ('defense_modifiers', (16,))):
                        if not any(s['id'] in ids for s in stats):
                            stats.extend(arrays.get(field, []))
                    key = json.dumps([row['txt_id'], stats], sort_keys=True)
                    if key in seen:
                        continue
                    seen.add(key)
                    check(stats, str(path), 'captured', item_base(row['txt_id']))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append({'source': str(path), 'error': str(exc)})

    endpoints = set()
    for family in ('identities', 'affixes'):
        for table, definitions in catalog[family].items():
            for definition in definitions.values():
                for key, limits in definition.get('roll_ranges', {}).items():
                    stat_id, _, layer = key.partition(':')
                    for bound in ('min', 'max'):
                        raw = limits[bound] * (1 << catalog['stats'][stat_id]['shift'])
                        if not raw:
                            continue
                        signature = (int(stat_id), int(layer or 0), raw)
                        if signature in endpoints:
                            continue
                        endpoints.add(signature)
                        if int(raw) != raw:
                            errors.append({'source': definition['name'], 'error': f'Nonintegral encoding: {key}'})
                            continue
                        check(
                            [{'id': signature[0], 'layer': signature[1], 'raw': int(raw)}],
                            f'{family}/{table}/{definition["name"]}/{key}/{bound}',
                            'catalog_endpoint',
                        )

    for family in ('identities', 'affixes'):
        for table in catalog[family].values():
            for definition in table.values():
                for effect in definition.get('fixed_triggers', []):
                    check(
                        [
                            {
                                'id': effect['stat_id'],
                                'layer': effect['skill_id'] * 64 + effect['level'],
                                'raw': effect['chance'],
                            }
                        ],
                        definition['name'],
                        'trigger',
                    )
                for effect in definition.get('fixed_per_level_effects', []):
                    check(
                        [{'id': effect['stat_id'], 'layer': 0, 'raw': effect['coefficient_raw']}],
                        definition['name'],
                        'level_formula',
                    )
                for effect in definition.get('variable_per_level_effects', []):
                    for raw in range(effect['minimum_raw'], effect['maximum_raw'] + 1, effect['step_raw']):
                        check([{'id': effect['stat_id'], 'layer': 0, 'raw': raw}], definition['name'], 'level_formula')
    for skill_id, skill in catalog['skills'].items():
        if skill.get('class'):
            check([{'id': 107, 'layer': int(skill_id), 'raw': 3}], skill['name'], 'class_skill')
    for class_id in range(8):
        check([{'id': 83, 'layer': class_id, 'raw': 2}], str(class_id), 'class_skill')
        for tree in range(3):
            check([{'id': 188, 'layer': class_id * 8 + tree, 'raw': 3}], str(class_id), 'class_skill')

    references = property_references(sources) if sources is not None else {}
    stats = []
    for stat_id, spec in sorted(catalog['stats'].items(), key=lambda pair: int(pair[0])):
        stats.append(
            {
                'id': int(stat_id),
                'name': spec['name'],
                'direct_property_sources': references.get(spec['name'], []),
                'evidence': dict(evidence[stat_id]),
                'status': 'exercised' if evidence[stat_id] else 'no_capture_or_roll_endpoint',
                'shift': spec.get('shift'),
                'encode': spec.get('encode'),
                'op': spec.get('op'),
                'op_base': spec.get('op_base'),
            }
        )
    return {
        'metadata_sha256': metadata_generation(),
        'reference_level': 91,
        'files': file_count,
        'distinct_captured_lists': len(seen),
        'distinct_catalog_endpoints': len(endpoints),
        'failures': failures,
        'input_errors': errors,
        'stats': stats,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', type=Path, default=Path('inventory_tracking/runs'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sources', type=Path, default=Path('third-parties/d2data/json'))
    args = parser.parse_args()
    result = audit(sorted(args.captures.rglob('*.json')), sources=args.sources)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'stats'}))
    return int(bool(result['failures'] or result['input_errors']))


if __name__ == '__main__':
    raise SystemExit(main())
