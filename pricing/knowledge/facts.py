"""Build portable unique/set facts from cached game tables without network access.

Raw property parameters are preserved: not every min/max pair is a numeric roll
range (charged skills, for example). Requirement reductions and inherent ethereal
flags are deliberately unresolved until their arithmetic has a verified adapter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path


_LABELS = {
    'hp': 'Life',
    'mana': 'Mana',
    'enr': 'Energy',
    'str': 'Strength',
    'dex': 'Dexterity',
    'vit': 'Vitality',
    'allskills': 'All skills',
    'sor': 'Sorceress skills',
    'fireskill': 'Fire skills',
    'cast1': 'Faster cast rate (%)',
    'cast2': 'Faster cast rate (%)',
    'cast3': 'Faster cast rate (%)',
    'balance1': 'Faster hit recovery (%)',
    'balance2': 'Faster hit recovery (%)',
    'balance3': 'Faster hit recovery (%)',
    'move1': 'Faster run/walk (%)',
    'move2': 'Faster run/walk (%)',
    'move3': 'Faster run/walk (%)',
    'regen-mana': 'Regenerate mana (%)',
    'mana-kill': 'Mana after each kill',
    'mag%': 'Better chance of magic items (%)',
    'res-all': 'All resistances',
    'res-fire': 'Fire resistance (%)',
    'res-cold': 'Cold resistance (%)',
    'res-ltng': 'Lightning resistance (%)',
    'res-pois': 'Poison resistance (%)',
    'ease': 'Requirements (%)',
    'nofreeze': 'Cannot be frozen',
    'half-freeze': 'Half freeze duration',
    'ac': 'Defense',
    'ac%': 'Enhanced defense (%)',
}
_SLOTS = {
    'head': 'head',
    'neck': 'amulet',
    'tors': 'body',
    'rrin': 'ring',
    'lrin': 'ring',
    'feet': 'feet',
    'glov': 'hands',
    'belt': 'waist',
}


def _read(path: Path, default=None):
    if not path.exists() and default is not None:
        return default
    return json.loads(path.read_text())


def _integer(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _stats(record):
    unconditional, conditional = [], []
    for field, prop in record.items():
        match = re.fullmatch(r'(a?)prop(\d+)([ab]?)', field)
        if not match or not prop:
            continue
        prefix, number, suffix = match.groups()
        stat = {
            'property': prop,
            'label': _LABELS.get(prop),
            'param': record.get(f'{prefix}par{number}{suffix}'),
            'min': record.get(f'{prefix}min{number}{suffix}'),
            'max': record.get(f'{prefix}max{number}{suffix}'),
            'source_field': field,
        }
        if prefix:
            mode = record.get('add func')
            stat['condition'] = {
                'add_func': mode,
                'group': int(number),
                'pieces_required': int(number) + 1 if mode == 2 else None,
            }
            conditional.append(stat)
        else:
            unconditional.append(stat)
    return unconditional, conditional


def _normalized_name(name):
    return re.sub(r'[^a-z0-9]', '', name.casefold())


def _reconcile(rows, catalog):
    census = {}
    for quality, category in (('unique', 'uniques'), ('set', 'sets')):
        facts = [row for row in rows if row['quality'] == quality]
        trades = [row for row in catalog if row.get('category') == category]
        fact_names = {_normalized_name(alias) for row in facts for alias in row['aliases']}
        trade_names = {_normalized_name(row['name']) for row in trades}
        for row in facts:
            aliases = {_normalized_name(alias) for alias in row['aliases']}
            row['catalog_ids'] = sorted(
                {str(t['catalog_id']) for t in trades if _normalized_name(t['name']) in aliases and t.get('catalog_id')}
            )
        set_names = {_normalized_name(row['set_name']) for row in facts if row.get('set_name')}
        bundle_names = sorted({r['name'] for r in trades if _normalized_name(r['name']) in set_names})
        census[quality] = {
            'fact_rows': len(facts),
            'catalog_set_bundle_names': bundle_names,
            'catalog_rows': len(trades),
            'unmatched_catalog_names': sorted(
                {r['name'] for r in trades if _normalized_name(r['name']) not in fact_names}
            ),
            'unmatched_fact_names': sorted(
                {r['name'] for r in facts if not any(_normalized_name(a) in trade_names for a in r['aliases'])}
            ),
            'matching': 'same quality and normalized exact display/internal alias; no fuzzy join',
        }
    return census


def build_item_facts(root: Path) -> dict:
    """Export every unique/set row, preserving inactive and unresolved records."""
    root = Path(root)
    raw = root / 'pricing/raw/d2data'
    bases = {}
    for table in ('weapons', 'armor', 'misc'):
        for key, record in _read(raw / f'{table}.json').items():
            bases[key] = (table, record)
    types = _read(raw / 'itemtypes.json')
    string_path = 'pricing/raw/mr/planners/game-strings.json'
    strings = {
        r[0]: r[1]
        for r in _read(root / string_path, [])
        if isinstance(r, list) and len(r) == 2 and isinstance(r[1], str)
    }
    rows = []
    for table, quality in (('uniqueitems', 'unique'), ('setitems', 'set')):
        for key, record in _read(raw / f'{table}.json').items():
            internal = record.get('index', str(key))
            name = strings.get(internal, internal)
            code = record.get('code' if quality == 'unique' else 'item')
            base_table, base = bases.get(code, (None, {}))
            stats, conditional = _stats(record)
            base_requirements = {
                'level': _integer(base.get('levelreq')),
                'strength': _integer(base.get('reqstr', 0)) if base else None,
                'dexterity': _integer(base.get('reqdex', 0)) if base else None,
            }
            level = _integer(record.get('lvl req'))
            if level is not None and base_requirements['level'] is not None:
                level = max(level, base_requirements['level'])
            requirements = {**base_requirements, 'level': level}
            modifiers = [s for s in stats if s['property'] in ('ease', 'ethereal')]
            if modifiers:
                requirements.update(strength=None, dexterity=None)
            item_type = base.get('type')
            type_record = types.get(item_type, {})
            bodyloc = type_record.get('BodyLoc1')
            slot = _SLOTS.get(bodyloc)
            if base_table == 'weapons':
                slot = 'weapon'
            elif bodyloc in ('rarm', 'larm'):
                slot = 'offhand'
            provenance = [{'path': f'pricing/raw/d2data/{table}.json', 'record_key': str(key)}]
            if base:
                provenance.append({'path': f'pricing/raw/d2data/{base_table}.json', 'record_key': code})
            if name != internal:
                provenance.append({'path': string_path, 'record_key': internal})
            item_id = f'd2data:{table}:{key}'
            rows.append(
                {
                    'id': item_id,
                    'item_id': item_id,
                    'kind': 'item_fact',
                    'name': name,
                    'aliases': sorted({name, internal}),
                    'quality': quality,
                    'category': base_table,
                    'base_code': code,
                    'base_id': f'd2data:{base_table}:{code}' if base else None,
                    'base_name': strings.get(base.get('namestr'), base.get('name', record.get('*ItemName'))),
                    'item_type': item_type,
                    'slot': slot,
                    'requirements': requirements,
                    'base_requirements': base_requirements,
                    'requirements_known': all(v is not None for v in requirements.values()),
                    'requirement_modifiers': modifiers,
                    'requirement_scope': 'original base, non-ethereal unless inherent; no upgrades or socket additions',
                    'drop_level': record.get('lvl'),
                    'stats': stats,
                    'set_name': strings.get(record.get('set'), record.get('set')),
                    'set_internal_name': record.get('set'),
                    'conditional_effects': conditional,
                    'set_wide_effects_known': False if quality == 'set' else None,
                    'availability': (
                        'spawnable'
                        if record.get('spawnable') == 1
                        else 'disabled'
                        if record.get('spawnable') == 0
                        else 'set_definition'
                        if quality == 'set'
                        else 'unverified'
                    ),
                    'availability_evidence': (
                        'explicit spawnable flag'
                        if 'spawnable' in record
                        else 'setitems row; no explicit spawnable flag'
                        if quality == 'set'
                        else 'unique spawnable flag absent'
                    ),
                    'provenance': provenance,
                    'source': f'pricing/raw/d2data/{table}.json',
                    'gaps': (['requirement modifier arithmetic unresolved'] if modifiers else [])
                    + (['base not resolved'] if not base else [])
                    + (['equip level missing'] if level is None else [])
                    + (['set-wide bonuses not in cached setitems table'] if quality == 'set' else []),
                }
            )
    catalog_path = 'pricing/data/appraisal-trade-catalog.json'
    catalog = _read(root / catalog_path, {'rows': []})['rows']
    census = _reconcile(rows, catalog)
    input_paths = [
        f'pricing/raw/d2data/{name}.json'
        for name in ('uniqueitems', 'setitems', 'weapons', 'armor', 'misc', 'itemtypes')
    ]
    input_paths += [string_path, catalog_path]
    manifest = [
        {'path': path, 'sha256': hashlib.sha256((root / path).read_bytes()).hexdigest()}
        for path in input_paths
        if (root / path).exists()
    ]
    return {
        'schema_version': 1,
        'adapter_version': 2,
        'adapter_updated_at': '2026-09-23',
        'generated_at': datetime.now(UTC).isoformat(),
        'input_manifest': manifest,
        'rows': rows,
        'coverage': {
            'catalog_reconciliation': census,
            'unique': sum(r['quality'] == 'unique' for r in rows),
            'set': sum(r['quality'] == 'set' for r in rows),
            'requirements_known': sum(r['requirements_known'] for r in rows),
            'unresolved_base': sum(r['base_code'] not in bases for r in rows),
            'set_wide_bonuses': 'unavailable: no cached sets table',
            'scope': 'all cached uniqueitems/setitems identities, including inactive rows',
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, default=Path('pricing/data/appraisal-item-facts.json'))
    args = parser.parse_args()
    payload = build_item_facts(args.root)
    output = args.output if args.output.is_absolute() else args.root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(payload['coverage']))


if __name__ == '__main__':
    main()
