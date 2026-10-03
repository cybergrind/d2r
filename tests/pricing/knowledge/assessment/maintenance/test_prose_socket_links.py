"""Abbreviated rune mentions must resolve through an already reviewed recipient."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint


ROOT = Path(__file__).resolve().parents[5]
ROLE = 'nova-sorceress-guide-2-vipermagi-ist'
OCCURRENCE = 'e2473f99a17fda0314c22944'


def inputs():
    def read(path):
        return json.loads((ROOT / path).read_text())

    occurrences = read('pricing/data/appraisal-guide-inventory.json')['occurrences']
    roles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    tables = read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
    occurrence = next(o for o in occurrences if o['id'] == OCCURRENCE)
    role = next(p for p in roles if p['id'] == ROLE)
    equipment_review = next(r for r in tables if r['profile_id'] == ROLE)
    equipment = next(o for o in occurrences if o['id'] == equipment_review['occurrence_id'])
    review = {
        'pattern_kind': 'structured_prose_socket',
        'occurrence_id': occurrence['id'],
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_id': ROLE,
        'profile_fingerprint': fingerprint(role),
        'equipment_occurrence_id': equipment['id'],
        'rune': 'Ist Rune',
        'variant_alias': 'MF',
        'review_date': '2026-09-30',
        'reason': 'MF prose replaces the armor facet with Ist; exact Vipermagi recipient and setup stay required.',
    }
    return review, occurrence, role, equipment_review, equipment, uses


def run(args):
    from pricing.knowledge.assessment.maintenance.prose_socket_links import validate_link
    from pricing.knowledge.assessment.maintenance.table_equivalence import _read

    return validate_link(*args, ROOT, lambda pin: json.loads(_read(ROOT, pin)))


def test_real_nova_prose_rune_reuses_exact_armor_configuration():
    result = run(inputs())
    assert result['occurrence_id'] == OCCURRENCE
    assert result['profile_id'] == ROLE
    assert result['state'] == 'reviewed'
    assert 'price' not in result


@pytest.mark.parametrize(
    'change', ['label', 'alias', 'rune', 'build', 'side', 'source', 'recipient', 'socket', 'fcr', 'endorsement']
)
def test_prose_summary_does_not_relax_recipient_or_setup(change):
    args = deepcopy(inputs())
    review, occurrence, role, equipment_review, equipment, uses = args
    if change == 'label':
        occurrence['original_label'] = occurrence['name'] = 'Ist rune (Hybrid variant)'
    elif change == 'alias':
        review['variant_alias'] = 'Hybrid'
    elif change == 'rune':
        review['rune'] = 'Um Rune'
    elif change == 'build':
        occurrence['build'] = 'lightning-sorceress'
    elif change == 'side':
        occurrence['side'] = 'merc'
    elif change == 'source':
        occurrence['source_locator'] = '/nova-sorceress-guide/prose_only_items/15'
    elif change == 'recipient':
        equipment['slot'] = 'Weapon'
    elif change in ('socket', 'fcr'):
        role['must']['all'] = [
            p
            for p in role['must']['all']
            if p.get('op') != ('socket_runes_equal' if change == 'socket' else 'context_at_least')
        ]
    else:
        uses[:] = [u for u in uses if u['profile_id'] != ROLE]
    review['occurrence_fingerprint'] = fingerprint(occurrence)
    review['profile_fingerprint'] = equipment_review['profile_fingerprint'] = fingerprint(role)
    equipment_review['occurrence_fingerprint'] = fingerprint(equipment)
    with pytest.raises(ValueError, match=r'[Pp]rose|[Nn]amed|[Ii]ncompatible'):
        run(args)


def test_prose_link_is_validated_by_completion_table_compiler():
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    review, occurrence, role, equipment_review, equipment, uses = inputs()
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': [review, equipment_review]},
        [occurrence, equipment],
        [role],
        [u for u in uses if u['profile_id'] == ROLE],
        ROOT,
    )
    assert {row['occurrence_id'] for row in result} == {OCCURRENCE, equipment['id']}


def test_summary_cannot_replace_missing_equipment_review():
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    review, occurrence, role, _, equipment, uses = inputs()
    with pytest.raises(ValueError, match='exactly one reviewed equipment link'):
        compile_table_equivalence(
            {'schema_version': 1, 'rows': [review]},
            [occurrence, equipment],
            [role],
            [u for u in uses if u['profile_id'] == ROLE],
            ROOT,
        )


def test_recorded_prose_link_closes_discovery_without_claiming_prices():
    from pricing.knowledge.assessment.maintenance.coverage_matrix import build_matrix

    def read(path):
        return json.loads((ROOT / path).read_text())

    matrix = build_matrix(
        read('pricing/data/appraisal-guide-inventory.json'),
        {'rows': []},
        {'rows': []},
        read('pricing/data/appraisal-build-profiles.json'),
        pattern_reviews=read('pricing/knowledge/assessment/rules/pattern_collection_reviews.json'),
        source_context_reviews=read('pricing/knowledge/assessment/rules/source_context_reviews.json'),
        hardcore_reviews=read('pricing/knowledge/assessment/rules/hardcore_reviews.json'),
        uses=read('pricing/knowledge/assessment/rules/guide_use_reviews.json'),
        table_reviews=read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json'),
    )
    row = next(r for r in matrix['rows'] if r.get('name') == 'Ist rune (MF variant)')
    assert row['dimensions']['discovery']['state'] == 'reviewed'
    assert row['occurrence_ids'] == [OCCURRENCE]
    for key in ('market', 'report', 'stat_annotations', 'socket_mechanics', 'recipe_eligibility'):
        assert row['dimensions'][key]['state'] == 'pending'
