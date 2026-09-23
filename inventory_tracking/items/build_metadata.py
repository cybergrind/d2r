"""Build bundled item metadata from explicitly supplied local game-data exports.

No network access. Run from the repository root. See data/README.md.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from pricing.knowledge.definitions import build_definitions


def build(stats_path, skills_path, output):
    root = Path(__file__).resolve().parents[2]
    strings = {
        r[0]: r[1]
        for r in json.loads((root / 'pricing/raw/mr/planners/game-strings.json').read_text())
        if isinstance(r, list) and len(r) == 2
    }
    props = json.loads((root / 'pricing/data/appraisal-properties.json').read_text())['properties']

    def norm(s):
        return re.sub(r'[^a-z0-9%{}+\-]', '', s.lower())

    labels = {}
    for pid, p in props.items():
        for label in p['labels']:
            labels.setdefault(norm(label), set()).add(pid)
    rows = {}
    for key, r in json.loads(stats_path.read_text()).items():
        template = strings.get(r.get('descstrpos'))
        label = None
        if (
            template
            and r.get('descfunc') in (19, 29)
            and not r.get('descstr2')
            and not r.get('Encode')
            and not r.get('Save Param Bits')
            and not r.get('Send Param Bits')
            and '%s' not in template
            and r['*ID'] not in (57, 58)
        ):
            label = template.replace('%+d', '+{{value}}').replace('%d', '{{value}}').replace('%%', '%')
        pids = labels.get(norm(label or ''), set())
        previous = rows.get(str(r['*ID']))
        rows[str(r['*ID'])] = {
            'name': key,
            'shift': r.get('ValShift', 0),
            'label': label,
            'template': template,
            'descfunc': r.get('descfunc', 0),
            'encode': r.get('Encode', 0),
            'op': r.get('op', 0),
            'op_param': r.get('op param', 0),
            'op_base': r.get('op base'),
            'parameter_bits': r.get('Save Param Bits', r.get('Send Param Bits', 0)),
            'property_id': next(iter(pids)) if len(pids) == 1 else None,
        }
        if previous:
            rows[str(r['*ID'])]['ambiguous_names'] = [previous['name'], key]
            rows[str(r['*ID'])]['label'] = None
            rows[str(r['*ID'])]['property_id'] = None
    bases = {}
    item_types = json.loads((root / 'pricing/raw/d2data/itemtypes.json').read_text())

    def is_blunt(code, seen=None):
        seen = set() if seen is None else seen
        if code == 'blun':
            return True
        if not code or code in seen:
            return False
        seen.add(code)
        row = item_types.get(code, {})
        return any(is_blunt(row.get(key), seen) for key in ('Equiv1', 'Equiv2'))

    for category in ('weapons', 'armor', 'misc'):
        for code, r in json.loads((root / f'pricing/raw/d2data/{category}.json').read_text()).items():
            cid = str(r['classid'])
            assert cid not in bases
            bases[cid] = {'name': r['name'], 'code': code, 'category': category, 'type': r.get('type')}
            if category == 'armor':
                bases[cid]['movement_penalty'] = r.get('speed')
            if category == 'weapons':
                bases[cid]['speed'] = r.get('speed')
                bases[cid]['undead_damage_bonus'] = 50 if is_blunt(r.get('type')) else 0
    skills = {
        str(r['*Id']): {'name': r['skill'], 'class': r.get('charclass')}
        for r in json.loads(skills_path.read_text()).values()
        if '*Id' in r and 'skill' in r
    }
    definitions = build_definitions(root)
    identities = {kind: {} for kind in ('set', 'unique', 'runeword')}
    affixes = {kind: {} for kind in ('prefix', 'suffix', 'auto')}
    for entry in definitions['rows']:
        if entry.get('affix_table'):
            affixes[entry['affix_table']][str(entry['table_id'])] = entry
        elif entry['table_id'] is not None:
            identities[entry['rarity']][str(entry['table_id'])] = entry
    data = {
        'provenance': {
            'date': '2026-09-23',
            'stats_url': 'https://raw.githubusercontent.com/blizzhackers/d2data/master/json/itemstatcost.json',
            'stats_sha256': hashlib.sha256(stats_path.read_bytes()).hexdigest(),
            'skills_url': 'https://raw.githubusercontent.com/blizzhackers/d2data/master/json/skills.json',
            'skills_sha256': hashlib.sha256(skills_path.read_bytes()).hexdigest(),
            'identities': definitions['inputs'],
            'bases': 'pricing/raw/d2data/{weapons,armor,misc}.json',
            'item_types': 'pricing/raw/d2data/itemtypes.json',
            'strings': 'pricing/raw/mr/planners/game-strings.json',
            'properties': 'pricing/data/appraisal-properties.json',
            'note': 'Static metadata does not validate memory layout or tooltip equivalence.',
        },
        'superior': {r['category']: r for r in definitions['rows'] if r['kind'] == 'quality_definition'},
        'identities': identities,
        'affixes': affixes,
        'affix_pools': definitions['affix_pools'],
        'staffmods': definitions['staffmods'],
        'rare_names': definitions['rare_names'],
        'bases': bases,
        'stats': rows,
        'skills': skills,
    }
    # Generated affix records contain large compatibility maps. One record per
    # line keeps the bundle reviewable without nearly a million indentation lines.
    sections = []
    for key, value in data.items():
        if key == 'affixes':
            tables = []
            for table, entries in affixes.items():
                records = [json.dumps(k) + ': ' + json.dumps(v) for k, v in entries.items()]
                tables.append(json.dumps(table) + ': {\n' + ',\n'.join(records) + '\n}')
            encoded = '{\n' + ',\n'.join(tables) + '\n}'
        else:
            encoded = json.dumps(value, indent=2)
        sections.append(json.dumps(key) + ': ' + encoded)
    output.write_text('{\n' + ',\n'.join(sections) + '\n}\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stats', type=Path, required=True)
    parser.add_argument('--skills', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'data/item_metadata.json')
    args = parser.parse_args()
    build(args.stats, args.skills, args.output)


if __name__ == '__main__':
    main()
