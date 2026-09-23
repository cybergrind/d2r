"""Preserve the existing catalog and curated evidence without upgrading its claims."""

import hashlib
import json
import re
from pathlib import Path


def _source(root, path):
    return {
        'id': path.stem,
        'path': str(path.relative_to(root)),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def import_catalog(root):
    root = Path(root)
    result = {'schema_version': 1, 'sources': [], 'rows': []}
    for path in sorted((root / 'pricing' / 'raw').glob('d2data-*.json')):
        source = _source(root, path)
        result['sources'].append(source)
        family = path.stem.removeprefix('d2data-')
        for code, item in json.loads(path.read_text()).items():
            if not isinstance(item, dict) or not item.get('name'):
                continue
            result['rows'].append(
                {
                    'name': item['name'],
                    'kind': 'catalog',
                    'category': family,
                    'base_code': item.get('code', code),
                    'source_id': source['id'],
                    'source_locator': code,
                    'details': {
                        'item_type': item.get('type'),
                        'max_sockets': item.get('gemsockets'),
                        'required_level': item.get('levelreq'),
                        'required_strength': item.get('reqstr'),
                        'required_dexterity': item.get('reqdex'),
                        'quality_level': item.get('level'),
                        'normal_code': item.get('normcode'),
                        'exceptional_code': item.get('ubercode'),
                        'elite_code': item.get('ultracode'),
                    },
                }
            )
    return result


def _bucket_facets(key):
    match = re.match(r'^(\d+)os/(eth|noneth)/([^/]+)', key)
    if not match:
        return {}
    return {'sockets': int(match[1]), 'ethereal': match[2] == 'eth', 'rarity': match[3]}


def _charm_name(key, row):
    category = row.get('class', '')
    if key.startswith('JW-facet'):
        return 'Rainbow Facet'
    if 'small' in category or key.startswith('CH-sc'):
        return 'Small Charm'
    if 'grand' in category or key.startswith('CH-gc'):
        return 'Grand Charm'
    if 'large' in category or key.startswith('CH-lc'):
        return 'Large Charm'
    if category.startswith('jewel'):
        return 'Jewel'
    return row.get('name') or row.get('bucket_def') or key


def import_legacy(root):
    root = Path(root)
    result = {'schema_version': 1, 'sources': [], 'rows': []}
    files = (
        'wp-b-prices.json',
        'wp-h-jewels-charms.json',
        'wp-i-uniques-misc.json',
        'wp-a-blues.json',
        'wp-c-anya.json',
        'wp-d-pickup.json',
        'wp-f-ladder.json',
    )
    for filename in files:
        path = root / 'pricing' / 'data' / filename
        if not path.exists():
            continue
        source = _source(root, path)
        result['sources'].append(source)
        data = json.loads(path.read_text())
        metadata = data.get('_meta', {})
        date = metadata.get('date') or metadata.get('pulled')
        for key, value in data.items():
            if key.startswith('_') or not isinstance(value, dict):
                continue
            common = {'source_id': source['id'], 'source_locator': key, 'date': value.get('date', date)}
            if filename == 'wp-b-prices.json':
                for bucket, evidence in value.get('buckets', {}).items():
                    result['rows'].append(
                        {
                            **common,
                            'name': value.get('name', key),
                            'kind': 'historical_market',
                            'scope_status': 'legacy_unverified',
                            'distinct_sellers': None,
                            'source_locator': f'{key}/buckets/{bucket}',
                            'bucket': bucket,
                            **_bucket_facets(bucket),
                            'details': evidence,
                            'caveat': 'Historical mixed-roll bucket; scope and seller counts unverified.',
                        }
                    )
            elif filename in ('wp-h-jewels-charms.json', 'wp-i-uniques-misc.json'):
                result['rows'].append(
                    {
                        **common,
                        'name': value.get('name') or _charm_name(key, value),
                        'kind': 'historical_market',
                        'category': value.get('class') or value.get('type'),
                        'scope_status': 'legacy_unverified',
                        'distinct_sellers': value.get('n_sellers'),
                        'bucket': key,
                        'details': value,
                        'caveat': 'Historical contextual evidence; mixed-economy references are not scoped fills.',
                    }
                )
            elif filename == 'wp-f-ladder.json':
                result['rows'].append(
                    {
                        **common,
                        'name': f'{key} Rune',
                        'kind': 'currency',
                        'category': 'runes',
                        'details': value,
                        'caveat': 'Dated conversion snapshot; not a fresh quote.',
                    }
                )
            else:
                name = key if filename == 'wp-a-blues.json' else value.get('item') or value.get('item_class') or key
                result['rows'].append(
                    {
                        **common,
                        'name': name,
                        'kind': 'keep_pattern',
                        'category': value.get('group') or value.get('kind'),
                        'details': value,
                        'caveat': 'Check source conditions; name similarity does not prove applicability.',
                    }
                )
    return result


def main():
    root = Path(__file__).resolve().parents[2]
    for filename, importer in (('appraisal-catalog.json', import_catalog), ('appraisal-legacy.json', import_legacy)):
        output = root / 'pricing' / 'data' / filename
        result = importer(root)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(f'{output}: {len(result["rows"])} records')


if __name__ == '__main__':
    main()
