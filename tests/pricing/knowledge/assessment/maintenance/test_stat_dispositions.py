"""Explicit exclusions must stay tied to the reviewed role and evidence."""

import hashlib
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.coverage_matrix import build_matrix
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_coverage_matrix import inputs


def case(tmp_path):
    data = inputs()
    path = tmp_path / 'guide'
    path.write_text('Three empty sockets; prepare the cited rune payload.')
    role = data[3]['profiles'][0]
    role['important_stats'] = []
    role['source']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    review = {
        'role_id': role['id'],
        'profile_fingerprint': fingerprint(role),
        'review_date': '2026-09-25',
        'disposition': 'no_stat_priority',
        'reason': 'Empty preparation base; source specifies fillers, no captured stat priority.',
    }
    return data, review


def test_only_explicit_stat_dimension_is_excluded(tmp_path):
    data, review = case(tmp_path)
    baseline = build_matrix(*data)
    result = build_matrix(*data, stat_dispositions=[review], source_root=tmp_path)
    for before, after in zip(baseline['rows'], result['rows'], strict=True):
        if after['kind'] != 'use_quality':
            assert after == before
            continue
        dims = deepcopy(after['dimensions'])
        stat = dims.pop('stat_desirability')
        assert stat['state'] == 'excluded'
        assert stat['reason'] == review['reason']
        assert stat['sources'][0]['evidence'] == data[3]['profiles'][0]['source']
        assert stat['sources'][0]['profile_fingerprint'] == review['profile_fingerprint']
        expected = deepcopy(before['dimensions'])
        assert expected.pop('stat_desirability')['state'] == 'pending'
        assert dims == expected
    assert not result['complete']


@pytest.mark.parametrize('change', ['profile', 'source', 'duplicate', 'reason', 'date', 'disposition', 'priority'])
def test_invalid_dispositions_cannot_close_review_queue(tmp_path, change):
    data, review = case(tmp_path)
    reviews = [review]
    if change == 'profile':
        data[3]['profiles'][0]['qualities'].append('crafted')
    elif change == 'source':
        (tmp_path / 'guide').write_text('Changed recommendation')
    elif change == 'duplicate':
        reviews.append(deepcopy(review))
    elif change == 'priority':
        data[3]['profiles'][0]['important_stats'] = ['31:0']
        review['profile_fingerprint'] = fingerprint(data[3]['profiles'][0])
    else:
        review[{'date': 'review_date'}.get(change, change)] = ''
    errors = {
        'profile': 'Stale',
        'source': 'Changed',
        'duplicate': 'Duplicate',
        'reason': 'reason',
        'date': 'Invalid isoformat',
        'disposition': 'Unsupported',
        'priority': 'conflicts',
    }
    with pytest.raises(ValueError, match=errors[change]):
        build_matrix(*data, stat_dispositions=reviews, source_root=tmp_path)


def test_configuration_conflict_is_rejected_even_without_important_stats(tmp_path):
    from pricing.knowledge.assessment.maintenance.stat_dispositions import validate_stat_dispositions

    data, review = case(tmp_path)
    data[3]['stat_evaluation'] = {'configurations': [{'role_id': review['role_id']}]}
    with pytest.raises(ValueError, match='conflicts'):
        validate_stat_dispositions([review], data[3], root=tmp_path)


def test_reviewed_exclusions_are_source_bound_and_do_not_waive_other_pending_roles():
    import json

    from pricing.knowledge.assessment.maintenance.inventory import ROOT
    from pricing.knowledge.assessment.maintenance.stat_dispositions import validate_stat_dispositions

    profiles = json.loads((ROOT / 'pricing/data/appraisal-build-profiles.json').read_text())
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_dispositions.json').read_text())
    result = validate_stat_dispositions(reviews, profiles, root=ROOT)
    assert set(result) == {
        'lightning-strike-amazon-topaz-crown-socket-base',
        'lightning-strike-amazon-resist-crown-socket-base',
        'berserk-barbarian-angelic-amulet',
        "berserk-barbarian-starter-set-Sigon's Wrap",
        'double-throw-barbarian-guide-angelic-amulet',
        'strafe-amazon-angelic-amulet',
        'dragon-talon-assassin-angelic-amulet',
        'echoing-strike-warlock-guide-angelic-amulet',
    }
    assert all(row['state'] == 'excluded' for row in result.values())
