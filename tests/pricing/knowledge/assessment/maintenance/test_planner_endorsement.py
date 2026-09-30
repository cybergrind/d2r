"""Planner-only use needs an explicit guide recommendation and exact equipment evidence."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.structured_named_variants import validate_link
from pricing.knowledge.assessment.maintenance.table_equivalence import _read


ROOT = Path(__file__).resolve().parents[5]
PID = 'fist-of-the-heavens-paladin-4-merc-andariel-native'
OID = '287434b2d5866c3275e9eb1e'


def read(path):
    return json.loads((ROOT / path).read_text())


def pin(path):
    return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


@pytest.fixture
def records():
    occurrence = next(o for o in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if o['id'] == OID)
    role = next(p for p in read('pricing/data/appraisal-build-profiles.json')['profiles'] if p['id'] == PID)
    use = next(
        u for u in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if u['profile_id'] == PID
    )
    planner_pin = pin('pricing/raw/mr/planners/s10106pr.json')
    planner = json.loads(read(planner_pin['path'])['data'])['planner']
    review = {
        'pattern_kind': 'structured_named_variant',
        'occurrence_id': OID,
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_id': PID,
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'canonical_name': "Andariel's Visage",
        'reason': (
            'Guide Summary explicitly recommends Holy Bolt Support; '
            'review intrinsic helmet independently of socket payload.'
        ),
        'review_date': '2026-09-29',
        'required_predicates': deepcopy(role['must']['all']),
        'required_conditions': deepcopy(role['conditions']),
        'planner_endorsement': {
            'guide': pin('pricing/data/appraisal-guide-sections.json'),
            'guide_source': 'pricing/raw/mr/guides__fist-of-the-heavens-paladin.html',
            'section_index': 52,
            'quote': 'You have the ability to carry group play with the holybolt support variant.',
            'variant_alias': 'holybolt support',
            'planner': planner_pin,
            'profile_index': 2,
            'profile_uid': 'GPIXhsmE',
            'profile_name': 'Holy Bolt Support',
            'player_class_code': 'pal',
            'mercenary_id': '10',
            'mercenary_type': 'Act 2 Holy Freeze',
            'slot': 'head',
            'item_id': '28',
            'expected_item': planner['items']['28'],
            'coverage': 'intrinsic_component',
            'socket_note': (
                'Jewel30 is15IAS/40ED; native-only helmet role does not certify that payload or a full IAS breakpoint.'
            ),
        },
    }
    return review, occurrence, role, use


def validate(records):
    review, occurrence, role, use = records
    return validate_link(review, occurrence, role, [use], ROOT, lambda ref: json.loads(_read(ROOT, ref)))


def test_explicit_guide_recommendation_can_endorse_native_planner_component(records):
    assert validate(records)['state'] == 'reviewed'


@pytest.mark.parametrize(
    'change',
    [
        'absent',
        'wrong-guide',
        'wrong-quote',
        'wrong-alias',
        'wrong-profile',
        'wrong-uid',
        'wrong-slot',
        'wrong-item',
        'changed-item',
        'wrong-merc',
        'wrong-class',
        'stale-planner',
        'missing-socket-note',
        'whole-loadout',
    ],
)
def test_shared_or_changed_planner_is_not_an_endorsement(records, change):
    evidence = records[0]['planner_endorsement']
    if change == 'absent':
        records[0].pop('planner_endorsement')
    elif change == 'changed-item':
        evidence['expected_item']['ethereal'] = False
    else:
        field, value = {
            'wrong-guide': ('guide_source', 'pricing/raw/mr/guides__abyss-warlock-build-guide.html'),
            'wrong-quote': ('quote', 'Any planner is a recommended build.'),
            'wrong-alias': ('variant_alias', 'standard'),
            'wrong-profile': ('profile_index', 0),
            'wrong-uid': ('profile_uid', 'not-the-profile'),
            'wrong-slot': ('slot', 'tors'),
            'wrong-item': ('item_id', '29'),
            'wrong-merc': ('mercenary_id', '11'),
            'wrong-class': ('player_class_code', 'nec'),
            'stale-planner': ('planner', {**evidence['planner'], 'sha256': '0' * 64}),
            'missing-socket-note': ('socket_note', ''),
            'whole-loadout': ('coverage', 'complete_loadout'),
        }[change]
        evidence[field] = value
    with pytest.raises(ValueError, match=r'[Pp]lanner|[Ee]ndorse|Guide|[Ii]ntrinsic|Stale table equivalence evidence'):
        validate(records)


def test_registered_holy_bolt_review_preserves_component_scope(records):
    rows = [
        row
        for row in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if row['occurrence_id'] == OID
    ]
    assert len(rows) == 1
    assert rows[0]['planner_endorsement']['coverage'] == 'intrinsic_component'
    assert rows[0]['required_conditions'] == records[2]['conditions']
    assert validate((rows[0], *records[1:]))['state'] == 'reviewed'


def test_equipment_branch_does_not_expand_named_component_scope(records):
    records[0]['planner_endorsement']['equipment_branches'] = {'': 0}
    with pytest.raises(ValueError, match=r'Equipment branch.*completed runeword'):
        validate(records)
