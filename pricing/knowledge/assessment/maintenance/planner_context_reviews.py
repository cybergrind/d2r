"""Narrow, pinned reviews of planner contexts outside player equipment."""

import hashlib
import json

from pricing.knowledge.builds import decode_planner


SKILLS = 'third-parties/d2data/json/skills.json'
EQUIPMENT = 'third-parties/d2data/json/monequip.json'
LEGACY = {f'third-parties/D2MOO/source/D2Game/src/SKILLS/{name}.cpp' for name in ('SkillAma', 'SkillNec', 'SkillAss')}


def _read(root, path, expected_hash):
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError('Context evidence outside repository')
    raw = resolved.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError('Stale planner context evidence')
    return raw


def _valkyrie(summon, evidence):
    if summon.get('monster') != 'valkyrie' or summon.get('group') != 'valkyrie' or summon.get('skill') != '32':
        return False
    skill = json.loads(evidence[SKILLS])['32']
    level = summon.get('skillLevel')
    if type(level) is not int or level < 1 or skill.get('summon') != 'valkyrie' or skill.get('calc2') != 'ln56':
        return False
    item_level = skill['Param5'] + skill['Param6'] * (level - 1)
    if summon.get('itemLevel') != item_level:
        return False
    expected = {}
    rows = json.loads(evidence[EQUIPMENT]).values()
    rows = sorted((r for r in rows if r.get('monster') == 'valkyrie'), key=lambda r: -r.get('level', 0))
    for row in rows:
        if row.get('level', 0) <= level:
            expected.setdefault(row['loc1'], (row['item1'], row['mod1']))
    items = summon.get('items', {})
    if not expected or items.keys() != expected.keys():
        return False
    # This reviewed cache contains inline rare items only. Other tiers or forms
    # need a separate review; native quality 6 is planner quality 4.
    return all(
        isinstance(items[slot], dict)
        and quality == 6
        and items[slot].get('quality') == 4
        and items[slot].get('base') == code
        and items[slot].get('ilvl') == item_level
        for slot, (code, quality) in expected.items()
    )


def apply_context_reviews(audit, documents, reviews, root):
    if reviews.get('schema_version') != 1 or not isinstance(reviews.get('rows'), list):
        raise ValueError('Invalid planner context reviews')
    seen = set()
    for row in reviews['rows']:
        if row['id'] in seen or not row.get('reason') or not row.get('reviewed_at'):
            raise ValueError('Invalid planner context review identity')
        seen.add(row['id'])
        if row['kind'] not in ('generated_valkyrie_equipment', 'abyss_resource_notes'):
            raise ValueError('Unsupported planner context review')
        source = row['source']
        original = decode_planner(json.loads(_read(root, source, row['source_sha256'])))
        planner = decode_planner(documents[source])
        if planner != original:
            raise ValueError('Changed planner context')
        evidence = {ref['path']: _read(root, ref['path'], ref['sha256']) for ref in row['evidence']}
        if row['kind'] == 'abyss_resource_notes':
            from pricing.knowledge.assessment.maintenance.planner_resource_notes import validate_resource_notes

            dependencies = validate_resource_notes(row, planner, evidence, root)
            audit.setdefault('source_hashes', {}).update(dependencies)
            issue = {'kind': 'notes_require_review'}
        else:
            summon = planner.get('summons', {}).get('valkyrie')
            if summon != row['expected_summon']:
                raise ValueError('Changed planner context')
            if set(evidence) != {SKILLS, EQUIPMENT, *LEGACY} or not _valkyrie(summon, evidence):
                raise ValueError('Unsupported generated equipment context')
            issue = {'kind': 'additional_equipment_context', 'path': '/summons/valkyrie/items'}
        report = audit['planner_reports'][source]
        if row['issue'] != issue or issue not in report['issues']:
            raise ValueError('Planner context issue mismatch')
        report['issues'].remove(issue)
        report.setdefault('reviewed_contexts', []).append(row)
