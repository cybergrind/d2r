"""Build bundled item metadata from explicitly supplied local game-data exports.

No network access. Run from the repository root. See data/README.md.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from inventory_tracking.items.stat_constants import HIT_EFFECT_DESCRIPTION_FUNCTION
from pricing.knowledge.assessment.maintenance.comparison_fillers import compile_fillers
from pricing.knowledge.assessment.maintenance.socket_scalars import compile_scalars
from pricing.knowledge.definitions import build_definitions
from pricing.knowledge.localization import merge_game_strings
from pricing.knowledge.named_upgrades import named_upgrade_variants


SCALAR_DESCRIPTION_FUNCTIONS = (19, 29)


def stat_label(row, template):
    """Market-style label for plain scalar rows and level-suffixed hit effects; None otherwise."""
    if (
        not template
        or row.get('descstr2')
        or row.get('Encode')
        or row.get('Save Param Bits')
        or row.get('Send Param Bits')
        or '%s' in template
        or row['*ID'] in (57, 58)
    ):
        return None
    if row.get('descfunc') in SCALAR_DESCRIPTION_FUNCTIONS:
        return template.replace('%+d', '+{{value}}').replace('%d', '{{value}}').replace('%%', '%')
    if row.get('descfunc') == HIT_EFFECT_DESCRIPTION_FUNCTION and '%' not in template:
        return template + ' +{{value}}'
    return None


def build_skills(rows, descriptions, strings):
    descriptions = {r['skilldesc']: r for r in descriptions.values() if r.get('skilldesc')}
    skills = {}
    for row in rows.values():
        if '*Id' not in row or 'skill' not in row:
            continue
        name = row['skill']
        if row.get('charclass'):
            key = descriptions.get(row.get('skilldesc'), {}).get('str name')
            localized = strings.get(key)
            if isinstance(localized, str) and localized.strip():
                name = localized
        skills[str(row['*Id'])] = {
            'name': name,
            **({'internal_name': row['skill']} if name != row['skill'] else {}),
            'class': row.get('charclass'),
            'required_level': row.get('reqlevel'),
            'maximum_level': row.get('maxlvl', 20),
        }
    return skills


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
        label = stat_label(r, template)
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

    raw_bases = {}
    for category in ('weapons', 'armor', 'misc'):
        for code, r in json.loads((root / f'pricing/raw/d2data/{category}.json').read_text()).items():
            raw_bases[code] = r
            cid = str(r['classid'])
            assert cid not in bases
            bases[cid] = {'name': r['name'], 'code': code, 'category': category, 'type': r.get('type')}
            if category == 'armor':
                bases[cid]['movement_penalty'] = r.get('speed')
            if category == 'weapons':
                bases[cid]['speed'] = r.get('speed')
                bases[cid]['undead_damage_bonus'] = 50 if is_blunt(r.get('type')) else 0
    skill_name_paths = [
        'third-parties/d2data/json/skilldesc.json',
        'third-parties/d2data/json/allstrings-eng.json',
        'pricing/raw/mr/planners/game-strings.json',
    ]
    skill_sources = [json.loads((root / path).read_text()) for path in skill_name_paths]
    skills = build_skills(
        json.loads(skills_path.read_text()), skill_sources[0], merge_game_strings(skill_sources[1], skill_sources[2])
    )
    definitions = build_definitions(root)
    identities = {kind: {} for kind in ('set', 'unique', 'runeword')}
    affixes = {kind: {} for kind in ('prefix', 'suffix', 'auto')}
    for entry in definitions['rows']:
        if entry.get('affix_table'):
            affixes[entry['affix_table']][str(entry['table_id'])] = entry
        elif entry['table_id'] is not None:
            if entry['rarity'] in ('unique', 'set'):
                entry = {**entry, 'upgrade_variants': named_upgrade_variants(entry, raw_bases)}
            identities[entry['rarity']][str(entry['table_id'])] = entry
    data = {
        'comparison_socket_effects': compile_fillers(
            json.loads((root / 'third-parties/d2data/json/gems.json').read_text()),
            json.loads((root / 'third-parties/d2data/json/properties.json').read_text()),
            rows,
        ),
        'fixed_socket_scalars': compile_scalars(
            json.loads((root / 'third-parties/d2data/json/gems.json').read_text()),
            json.loads((root / 'third-parties/d2data/json/properties.json').read_text()),
            rows,
            raw_bases,
        ),
        'provenance': {
            'date': '2026-09-23',
            'stats_url': 'https://raw.githubusercontent.com/blizzhackers/d2data/master/json/itemstatcost.json',
            'stats_sha256': hashlib.sha256(stats_path.read_bytes()).hexdigest(),
            'skills_url': 'https://raw.githubusercontent.com/blizzhackers/d2data/master/json/skills.json',
            'skills_sha256': hashlib.sha256(skills_path.read_bytes()).hexdigest(),
            'skill_names': {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in skill_name_paths},
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
        'crafting_bases': definitions['crafting_bases'],
        'crafting_nonethereal': definitions['crafting_nonethereal'],
        'crafting_triggers': definitions['crafting_triggers'],
        'crafting_affix_only_cold': definitions['crafting_affix_only_cold'],
        'crafting_affix_only_poison': definitions['crafting_affix_only_poison'],
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
