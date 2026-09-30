"""Exact Abyss resource-note review, with executable role and policy dependencies."""

import hashlib
import json

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint


ROLE = 'abyss-warlock-insight-act-2-might'
ROLE_PATH = 'pricing/knowledge/assessment/rules/roles/abyss-warlock-build-guide.json'
POLICY = 'pricing/knowledge/assessment/policies/consumables.py'
MISC = 'third-parties/d2data/json/misc.json'
SKILLS = 'third-parties/d2data/json/skills.json'
PARTS = [
    {
        'quote': 'Bind Cursed Conviction Hephasto. Consume Defiler.',
        'disposition': 'skill_usage',
        'skills': ['381', '382'],
    },
    {'quote': 'If you have Mana Issues, use Insight instead.', 'disposition': 'reviewed_role', 'role_id': ROLE},
    {'quote': 'Also, just drink your ding dang potions. You silly goose.', 'disposition': 'ordinary_recovery_policy'},
    {'quote': '- Mac', 'disposition': 'author_signature'},
]


def text_nodes(value):
    if isinstance(value, dict):
        if isinstance(value.get('text'), str):
            yield value['text']
        for child in value.get('children', []):
            yield from text_nodes(child)


def validate_resource_notes(row, planner, evidence, root):
    notes = planner.get('notes')
    if notes != row.get('expected_notes'):
        raise ValueError('Changed resource note')
    expected_text = [PARTS[0]['quote'], PARTS[1]['quote'] + ' ' + PARTS[2]['quote'], PARTS[3]['quote']]
    if row.get('parts') != PARTS or list(text_nodes(notes.get('root', {}))) != expected_text:
        raise ValueError('Incomplete or unsupported resource note review')
    if set(evidence) != {POLICY, MISC, SKILLS}:
        raise ValueError('Missing resource note policy evidence')
    skills = json.loads(evidence[SKILLS])
    if any(
        skills[key].get('skill') != name or skills[key].get('charclass') != 'war'
        for key, name in [('381', 'Consume'), ('382', 'Bind Demon')]
    ):
        raise ValueError('Changed resource note skill context')
    reference = row['role_reference']
    if reference['path'] != ROLE_PATH or reference['id'] != ROLE:
        raise ValueError('Unsupported resource note role')
    raw = (root / ROLE_PATH).read_bytes()
    role = next((r for r in json.loads(raw)['profiles'] if r['id'] == ROLE), None)
    if role is None or fingerprint(role) != reference['fingerprint']:
        raise ValueError('Stale resource note role')
    return {ROLE_PATH: hashlib.sha256(raw).hexdigest()}
