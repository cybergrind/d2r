"""Offline, source-preserving build and planner demand import.

Run ``python -m pricing.knowledge.builds`` to rebuild portable demand evidence.
No networking occurs here; research/maintenance supplies the source cache.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def decode_planner(document):
    data = document.get('data', document)
    if isinstance(data, str):
        data = json.loads(data)
    planner = data.get('planner', data)
    if not isinstance(planner.get('items'), dict) or not isinstance(planner.get('profiles'), list):
        raise ValueError('Planner must contain items and profiles')
    return planner


def load_catalog(root=ROOT):
    root = Path(root)
    data = json.loads((root / 'pricing/raw/mr/planners/game-data.json').read_text())
    strings = {
        x[0]: x[1]
        for x in json.loads((root / 'pricing/raw/mr/planners/game-strings.json').read_text())
        if isinstance(x, list) and len(x) > 1
    }
    catalog = {}
    for group, category in [
        ('armor', 'armor'),
        ('weapons', 'weapon'),
        ('misc', 'misc'),
        ('uniqueItems', 'unique'),
        ('setItems', 'set'),
        ('runes', 'runeword'),
    ]:
        for key, item in data[group].items():
            label = item.get('namestr') or item.get('index') or item.get('name') or key
            catalog[key] = {
                'name': strings.get(label, label),
                'category': category,
                'base_code': item.get('code', item.get('item')),
                'catalog_id': key,
                'aliases': [label]
                if strings.get(label, label) != label and group in ('uniqueItems', 'setItems')
                else [],
            }
    for group, category in [
        ('armor', 'armor'),
        ('weapons', 'weapon'),
        ('misc', 'misc'),
        ('uniqueitems', 'unique'),
        ('setitems', 'set'),
        ('runes', 'runeword'),
    ]:
        path = root / f'pricing/raw/d2data/{group}.json'
        if not path.exists():
            continue
        for code, item in json.loads(path.read_text()).items():
            if group in ('uniqueitems', 'setitems'):
                if '*ID' not in item:
                    continue
                key = ('unique' if group == 'uniqueitems' else 'set') + f'{int(item["*ID"]):03d}'
                name = item.get('index', code)
            elif group == 'runes':
                if not item.get('complete') or 'lineNumber' not in item:
                    continue
                key = f'runeword{int(item["lineNumber"]) + 27:03d}'
                name = item.get('*Rune Name', code)
            else:
                key = code
                name = item.get('name', code)
            existing = catalog.get(key)
            if existing and existing['name'] != name:
                existing.setdefault('aliases', []).append(name)
            catalog.setdefault(
                key,
                {
                    'name': name,
                    'category': category,
                    'base_code': item.get('code', item.get('item')),
                    'catalog_id': key,
                },
            )
    return catalog


def _record(name, source_id, locator, build, class_name, variant, side, slot, **extra):
    identity = f'{source_id}:{build}:{locator}'
    return {
        'id': hashlib.sha256(identity.encode()).hexdigest()[:24],
        'name': name,
        'original_label': name,
        'kind': 'demand',
        'source_id': source_id,
        'source_locator': locator,
        'build': build,
        'class': class_name,
        'variant': variant,
        'side': side,
        'slot': str(slot),
        **extra,
    }


def planner_rows(document, catalog, source_id, build, class_name):
    planner = decode_planner(document)
    rows = []
    used = set()
    unresolved = 0
    reconciled_sets = []

    def add(ref, locator, profile, side, slot, container, ancestors=()):
        nonlocal unresolved
        if ref is None:
            return
        key = str(ref)
        if key in ancestors:
            raise ValueError(f'Cyclic socket reference at {locator}')
        item = ref if isinstance(ref, dict) else planner['items'].get(key)
        if item is not None:
            used.add(key)
        else:
            item = {'base': key}
        identity = item.get('unique') or item.get('base', '')
        resolved = catalog.get(identity)
        base = catalog.get(item.get('base'), {})
        name = resolved['name'] if resolved else f'Unresolved item {identity or key}'
        if not resolved:
            unresolved += 1
        if resolved and not item.get('unique') and item.get('quality') in (3, 4, 8):
            name = {3: 'Magic ', 4: 'Rare ', 8: 'Crafted '}[item['quality']] + name
        recommended = not re.search(r'skill|testing|^set \d+$|embed|unreferenced', profile.get('name', ''), re.I)
        details = {
            **item,
            'container': container,
            'item_ref': key,
            'profile_uid': profile.get('uid'),
            'profile_date': document.get('date'),
            'mercenary_id': profile.get('merc'),
            'role': 'socket_filler' if container == 'socketedItems' else container,
            'recommended': recommended,
            'resolution_status': 'resolved' if resolved else 'unresolved',
            'base_name': base.get('name'),
            'canonical_id': identity if resolved else None,
        }
        rows.append(
            _record(
                name,
                source_id,
                locator,
                build,
                class_name,
                profile.get('name', 'Unnamed'),
                side,
                slot,
                category=(resolved or {}).get('category'),
                base_code=item.get('base'),
                aliases=(resolved or {}).get('aliases', []),
                sockets=item.get('sockets'),
                ethereal=item.get('ethereal'),
                rarity={3: 'magic', 4: 'rare', 5: 'set', 6: 'unique', 7: 'runeword', 8: 'crafted'}.get(
                    item.get('quality')
                ),
                predicates={k: item[k] for k in ('sockets', 'ethereal', 'quality') if k in item},
                details=details,
            )
        )
        for i, child in enumerate(item.get('socketedItems', [])):
            add(child, f'{locator}/socketedItems/{i}', profile, side, slot, 'socketedItems', (*ancestors, key))

    for i, profile in enumerate(planner['profiles']):
        count = len(rows)
        for container, side in [
            ('items', 'player'),
            ('mercItems', 'merc'),
            ('inventory', 'player'),
            ('cube', 'player'),
        ]:
            values = profile.get(container, {})
            pairs = values.items() if isinstance(values, dict) else enumerate(values)
            for slot, ref in pairs:
                add(ref, f'/profiles/{i}/{container}/{slot}', profile, side, slot, container)
        reconciled_sets.append({'uid': profile.get('uid'), 'name': profile.get('name'), 'rows': len(rows) - count})
    unused = sorted(set(planner['items']) - used)
    for key in unused:
        add(key, f'/items/{key}', {'name': 'Unreferenced definitions'}, 'unspecified', key, 'unreferenced_definition')
        rows[-1]['details']['recommended'] = False
    return rows, {
        'sets': len(planner['profiles']),
        'set_details': reconciled_sets,
        'item_definitions': len(planner['items']),
        'referenced_item_definitions': len(planner['items']) - len(unused),
        'unreferenced_item_ids': unused,
        'unresolved_references': unresolved,
    }


def _source(root, path, url=None, fetched_at=None):
    return {
        'id': str(path.relative_to(root)),
        'path': str(path.relative_to(root)),
        'url': url,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'fetched_at': fetched_at,
        'parser_version': 'builds-1',
    }


class _Mentions(HTMLParser):
    def __init__(self):
        super().__init__()
        self.mentions = []
        self.active = None
        self.depth = 0
        self.cell = 0
        self.slot = ''
        self.in_row = False
        self.heading = ''
        self.in_heading = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('h2', 'h3'):
            self.heading = ''
            self.in_heading = True
        if tag == 'tr':
            self.in_row, self.cell, self.slot = True, 0, ''
        if tag in ('td', 'th'):
            self.cell += 1
        if tag == 'span':
            if self.active:
                self.depth += 1
            elif 'd2planner-item' in attrs.get('class', '') or (
                'data-d2-id' in attrs and any(x in attrs.get('class', '') for x in ('item', 'tooltip'))
            ):
                self.active = {
                    'item_id': attrs.get('data-d2planner-id', attrs.get('data-d2-id', '')),
                    'profile_id': attrs.get('data-d2planner-profile'),
                    'label': '',
                    'slot': self.slot.strip() or 'unspecified',
                    'side': 'merc' if 'merc' in self.heading.lower() else 'player',
                }
                self.depth = 1

    def handle_data(self, data):
        if self.in_heading:
            self.heading += data
        if self.in_row and self.cell == 1:
            self.slot += data
        if self.active:
            self.active['label'] += data

    def handle_endtag(self, tag):
        if tag in ('h2', 'h3'):
            self.in_heading = False
        if tag == 'tr':
            self.in_row = False
        if tag == 'span' and self.active:
            self.depth -= 1
            if not self.depth:
                self.active['label'] = ' '.join(self.active['label'].split())
                self.mentions.append(self.active)
                self.active = None


def guide_mentions(html):
    parser = _Mentions()
    parser.feed(html)
    return parser.mentions


def build_dataset(root=ROOT):
    root = Path(root)
    inventory = json.loads((root / 'pricing/data/appraisal-build-source-inventory-2026-09-23.json').read_text())
    ledger = json.loads((root / 'pricing/data/wp-a-builds.json').read_text())
    catalog = load_catalog(root)
    review_path = root / 'pricing/data/appraisal-build-variant-review-2026-09-23.json'
    reviews = json.loads(review_path.read_text()) if review_path.exists() else {}
    sources = {}
    if reviews:
        sources[str(review_path.relative_to(root))] = _source(root, review_path)
    rows = []
    coverage = {'guides': {}, 'planners': {}, 'unresolved_labels': []}
    profile_builds = {}
    name_catalog = {name.casefold(): v for v in catalog.values() for name in [v['name'], *v.get('aliases', [])]}
    for slug in inventory['mandatory_top_builds']:
        path = root / f'pricing/raw/mr/guides__{slug}.html'
        html = unescape(path.read_text())
        sid = str(path.relative_to(root))
        sources[sid] = _source(
            root, path, f'https://maxroll.gg/d2/guides/{slug}', '2026-09-18' if slug in ledger else '2026-09-23'
        )
        class_name = ledger.get(slug, {}).get('class') or next(
            (
                c
                for c in ['Warlock', 'Sorceress', 'Paladin', 'Amazon', 'Assassin', 'Druid', 'Barbarian', 'Necromancer']
                if c.casefold() in slug
            ),
            'Unknown',
        )
        ids = set(re.findall(r'data-(?:d2-id|d2planner-profile)=["\']([a-z0-9]{8})["\']', html))
        for pid in ids:
            profile_builds.setdefault(pid, set()).add((slug, class_name))
        before = len(rows)
        for i, mention in enumerate(guide_mentions(html)):
            item_id, label = mention['item_id'], mention['label']
            found = catalog.get(item_id.split('-')[0]) or name_catalog.get(label.casefold())
            if not found and not label:
                continue
            name = found['name'] if found else label
            rows.append(
                _record(
                    name,
                    sid,
                    f'/item-spans/{i}',
                    slug,
                    class_name,
                    'Guide mention',
                    mention['side'],
                    mention['slot'],
                    category=(found or {}).get('category'),
                    details={
                        'role': 'guide_mention',
                        'raw_item_id': item_id,
                        'original_label': label,
                        'profile_id': mention['profile_id'],
                        'resolution_status': 'resolved' if found else 'pattern_or_unresolved',
                        'recommended': True,
                    },
                )
            )
        b = ledger.get(slug, {})
        ledger_path = root / 'pricing/data/wp-a-builds.json'
        lsid = str(ledger_path.relative_to(root))
        sources[lsid] = _source(root, ledger_path)

        def label_row(label, locator, variant, side, slot, lsid=lsid, slug=slug, class_name=class_name):
            found = name_catalog.get(label.casefold())
            rows.append(
                _record(
                    label,
                    lsid,
                    f'/{slug}/{locator}',
                    slug,
                    class_name,
                    variant,
                    side,
                    slot,
                    category=(found or {}).get('category'),
                    details={
                        'role': 'documented_alternative',
                        'recommended': True,
                        'resolution_status': 'resolved' if found else 'pattern_or_unresolved',
                    },
                )
            )

        for slot, labels in b.get('slots', {}).items():
            for i, label in enumerate(labels):
                label_row(label, f'slots/{slot}/{i}', 'Main alternatives', 'player', slot)
        for slot, stages in b.get('merc', {}).items():
            if isinstance(stages, dict):
                for stage, labels in stages.items():
                    for i, label in enumerate(labels or []):
                        label_row(label, f'merc/{slot}/{stage}/{i}', stage, 'merc', slot)
        for vi, variant in enumerate(b.get('variants', [])):
            for side in ('player', 'merc'):
                for slot, labels in variant.get(side, {}).items():
                    if not isinstance(labels, list):
                        continue
                    for i, label in enumerate(labels):
                        label_row(label, f'variants/{vi}/{side}/{slot}/{i}', variant['name'], side, slot)
        for i, label in enumerate(b.get('prose_only_items', [])):
            label_row(label, f'prose_only_items/{i}', 'Prose alternatives', 'unspecified', 'unspecified')
        variant_file = root / f'pricing/data/wp-a-variants/{slug}.json'
        if variant_file.exists():
            source_notes = json.dumps(json.loads(variant_file.read_text()).get('sources', {}))
            for pid in re.findall(r'\b[a-z0-9]{8}\b', source_notes):
                if any(c.isdigit() for c in pid) and (root / f'pricing/raw/mr/planners/{pid}.json').exists():
                    profile_builds.setdefault(pid, set()).add((slug, class_name))
        coverage['guides'][slug] = {
            'status': 'parsed',
            'planner_ids': sorted(ids),
            'guide_rows': len(rows) - before,
            'main_table_source': 'reviewed_ledger' if b else 'linked_item_mentions',
            'manual_variant_review': bool(b) or slug in reviews,
            'variant_review': reviews.get(slug),
        }
    for pid in sorted(profile_builds):
        path = root / f'pricing/raw/mr/planners/{pid}.json'
        sid = str(path.relative_to(root))
        document = json.loads(path.read_text())
        sources[sid] = _source(root, path, f'https://planners.maxroll.gg/profiles/d2/{pid}', '2026-09-23')
        if 'data' not in document:
            coverage.setdefault('unavailable_planners', {})[pid] = {
                'status': 'source_download_failure404',
                'response': document,
            }
            continue
        sources[sid]['source_updated_at'] = document.get('date')
        associations = sorted(profile_builds.get(pid, set()))
        slug, class_name = associations[0] if len(associations) == 1 else ('shared-planner', 'Multiple')
        imported, counts = planner_rows(document, catalog, sid, slug, class_name)
        for row in imported:
            row['details']['related_builds'] = [x[0] for x in associations]
            row['details']['related_classes'] = sorted({x[1] for x in associations})
            row['details']['recommendation_status'] = 'planner evidence; guide association is not set endorsement'
            row['details']['recommended'] = False
            row['details']['historical'] = (document.get('date') or '') < '2026'
        rows.extend(imported)
        coverage['planners'][pid] = counts
    for path in [
        *sorted((root / 'pricing/raw/d2data').glob('*.json')),
        root / 'pricing/raw/mr/planners/game-data.json',
        root / 'pricing/raw/mr/planners/game-strings.json',
    ]:
        sources[str(path.relative_to(root))] = _source(root, path, fetched_at='2026-09-23')
    coverage['occurrences'] = len(rows)
    coverage['guide_count'] = len(coverage['guides'])
    coverage['planner_count'] = len(coverage['planners'])
    coverage['sets'] = sum(x['sets'] for x in coverage['planners'].values())
    coverage['item_definitions'] = sum(x['item_definitions'] for x in coverage['planners'].values())
    coverage['unresolved_rows'] = sum(
        r['details']['resolution_status'] in ('unresolved', 'pattern_or_unresolved') for r in rows
    )
    return {
        'schema_version': 1,
        'generated_at': datetime.now(UTC).isoformat(),
        'sources': list(sources.values()),
        'rows': rows,
        'coverage': coverage,
    }


def main():
    result = build_dataset()
    path = ROOT / 'pricing/data/appraisal-demand.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result['coverage'].items() if not isinstance(v, (dict, list))}))


if __name__ == '__main__':
    main()
