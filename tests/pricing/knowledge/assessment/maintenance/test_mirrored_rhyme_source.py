"""Starter Rhyme is tied to its actual tab, planner and staffmod configuration."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_chaos_enigma_source import records as enigma_records
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import pin, read, validate
from tests.pricing.knowledge.assessment.maintenance.test_prose_named_alternatives import records as named_records


PID = 'mirrored-starter-rhyme-grimoire'
OID = 'd555979e868837ef52c42453'


def records():
    review, occurrence, role, use = named_records(PID, OID, 'Rhyme')
    evidence = deepcopy(enigma_records()[0]['planner_endorsement'])
    planner = pin('pricing/raw/mr/planners/rg2je0ld.json')
    evidence.update(
        guide_source='pricing/raw/mr/guides__mirrored-blades-warlock-guide.html',
        section_index=12,
        quote='As a Warlock, keep in mind that you can wield a 2-Handed Weapon in a single hand.',
        variant_alias='Starter',
        guide_tab='Starter',
        planner=planner,
        profile_index=0,
        profile_uid='8IRFWTHa',
        profile_name='Starter',
        player_class_code='war',
        slot='larm',
        item_id='10',
        expected_item=decode_planner(read(planner['path']))['items']['10'],
    )
    review.update(
        reason=(
            'Starter tab embeds this actual profile and Rhyme Grimoire. Review requires all three cited '
            'staffmods together, not a different swap shield. Omitted ethereal flag is not inferred; '
            'this use remains nonethereal-only.'
        ),
        planner_endorsement=evidence,
    )
    return review, occurrence, role, use


def test_starter_tab_proves_exact_rhyme_configuration():
    assert validate(records())['state'] == 'reviewed'


@pytest.mark.parametrize('change', ['other-tab', 'other-profile', 'missing-tab', 'other-quote'])
def test_starter_endorsement_cannot_use_neighboring_evidence(change):
    data = records()
    evidence = data[0]['planner_endorsement']
    if change == 'other-tab':
        evidence['guide_tab'] = 'Ubers'
    elif change == 'other-profile':
        evidence['profile_uid'] = 'unrelated'
    elif change == 'missing-tab':
        evidence.pop('guide_tab')
    else:
        evidence['quote'] = 'Use anything from any planner.'
    with pytest.raises(ValueError, match='Guide does not establish'):
        validate(data)


@pytest.mark.parametrize('skill', ['107:392', '107:389', '107:377'])
def test_review_requires_each_cited_staffmod(skill):
    review, occurrence, role, use = records()
    role['must']['all'] = [p for p in role['must']['all'] if p.get('key') != skill]
    use['profile_fingerprint'] = review['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='lost mandatory reviewed predicates'):
        validate((review, occurrence, role, use))


def test_registered_starter_rhyme_preserves_tab_and_staffmods():
    _, occurrence, role, use = records()
    matches = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == OID
    ]
    assert len(matches) == 1
    assert matches[0]['required_predicates'] == role['must']['all']
    assert matches[0]['planner_endorsement']['guide_tab'] == 'Starter'
    assert validate((matches[0], occurrence, role, use))['state'] == 'reviewed'
