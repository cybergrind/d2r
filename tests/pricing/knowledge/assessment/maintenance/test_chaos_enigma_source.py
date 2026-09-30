"""Chaos Prep's explicitly recommended player recipe retains exact equipment proof."""

import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import pin, read, validate


PID = 'berserk-barbarian-4-player-enigma'
OID = '844e7d3daba32cb50dd8de91'


def records():
    role = next(r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == PID)
    use = next(
        r for r in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if r['profile_id'] == PID
    )
    occurrence = next(r for r in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if r['id'] == OID)
    planner = pin('pricing/raw/mr/planners/rb1d60lu.json')
    evidence = {
        'guide': pin('pricing/data/appraisal-guide-sections.json'),
        'guide_source': 'pricing/raw/mr/guides__berserk-barbarian.html',
        'section_index': 25,
        'quote': (
            'Even in a full game, this build can spawn Diablo incredibly fast by focusing on popping Seals and '
            'assassinating the Seal Boss Super Uniques. See the "Chaos Prep" Build Variant '
            'to learn more about this strategy.'
        ),
        'variant_alias': 'Chaos Prep',
        'planner': planner,
        'profile_index': 3,
        'profile_uid': 'H4WR4Vbt',
        'profile_name': 'Chaos Prep',
        'player_class_code': 'bar',
        'slot': 'tors',
        'item_id': '3',
        'expected_item': decode_planner(read(planner['path']))['items']['3'],
        'coverage': 'player_runeword_component',
        'ethereal_scope': 'nonethereal_only',
        'recipe_sources': {
            key: pin(path)
            for key, path in {
                'planner': 'pricing/raw/mr/planners/game-data.json',
                'runes': 'third-parties/d2data/json/runes.json',
                'armor': 'third-parties/d2data/json/armor.json',
                'types': 'third-parties/d2data/json/itemtypes.json',
            }.items()
        },
    }
    review = {
        'pattern_kind': 'structured_named_variant',
        'occurrence_id': OID,
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_id': PID,
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'canonical_name': 'Enigma',
        'review_date': '2026-09-29',
        'reason': (
            'Explicit Chaos Prep guide endorsement and exact player Mage Plate with Jah/Ith/Ber. '
            'Review is nonethereal-only; the omitted planner ethereal flag is not evidence of false. '
            'Defense rolls are not entry gates or numeric price premiums.'
        ),
        'required_predicates': deepcopy(role['must']['all']),
        'required_conditions': deepcopy(role['conditions']),
        'planner_endorsement': evidence,
    }
    return review, occurrence, role, use


def test_explicit_chaos_prep_endorsement_accepts_player_enigma():
    assert validate(records())['state'] == 'reviewed'


@pytest.mark.parametrize('field', ['ethereal_scope', 'profile_uid', 'slot', 'player_class_code'])
def test_player_recipe_cannot_drop_scope_or_change_wearer(field):
    data = records()
    data[0]['planner_endorsement'][field] = 'wrong'
    with pytest.raises(ValueError, match=r'[Ee]ndorsed|[Pp]lanner'):
        validate(data)


def test_uncited_planner_is_rejected_even_when_profile_matches():
    from pricing.knowledge.assessment.maintenance.planner_endorsement import validate_endorsement
    from pricing.knowledge.assessment.maintenance.table_equivalence import _read
    from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import ROOT

    review, _, role, _ = records()
    build = read('pricing/data/wp-a-builds.json')['berserk-barbarian']
    build['variants_sources']['planner_id'] = 'unrelated'
    with pytest.raises(ValueError, match='not a cited source'):
        validate_endorsement(review, role, build, ROOT, lambda ref: json.loads(_read(ROOT, ref)))


def test_registered_chaos_enigma_keeps_player_recipe_proof():
    _, occurrence, role, use = records()
    matches = [
        row
        for row in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if row['occurrence_id'] == OID
    ]
    assert len(matches) == 1
    assert matches[0]['required_predicates'] == role['must']['all']
    assert matches[0]['required_conditions'] == role['conditions']
    assert matches[0]['planner_endorsement']['coverage'] == 'player_runeword_component'
    assert validate((matches[0], occurrence, role, use))['state'] == 'reviewed'
