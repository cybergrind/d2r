from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.coverage_matrix import build_matrix


def inputs():
    return (
        {
            'identities': [
                {
                    'id': 'u',
                    'name': 'Unmentioned',
                    'category': 'unique',
                    'catalog_ids': ['unique1'],
                    'occurrence_ids': [],
                },
                {
                    'id': 'x',
                    'name': 'Unknown pattern',
                    'category': 'unresolved',
                    'catalog_ids': [],
                    'occurrence_ids': ['o'],
                },
            ],
            'occurrences': [{'id': 'o', 'identity_id': 'x'}],
        },
        {
            'rows': [
                {
                    'id': 'base:normal',
                    'base_code': 'base',
                    'quality': 'normal',
                    'name': 'Base',
                    'dimensions': {
                        'socket_mechanics': {'state': 'reviewed', 'reason': 'Native limits verified'},
                        'desirability': {'state': 'pending', 'reason': 'Candidates only'},
                    },
                }
            ]
        },
        {
            'rows': [
                {
                    'name': 'Unmentioned',
                    'quality': 'unique',
                    'status': 'reviewed_policy',
                    'tier': 'low',
                    'source_error': None,
                    'research_locator': '/U',
                }
            ]
        },
        {
            'profiles': [
                {
                    'id': 'role',
                    'qualities': ['magic', 'rare'],
                    'types': ['ring'],
                    'review_status': 'reviewed_candidate_rule',
                    'source': {'path': 'guide', 'locator': '/ring'},
                }
            ]
        },
    )


def test_matrix_retains_unmentioned_and_unresolved_identities_and_independent_dimensions():
    data = inputs()
    result = build_matrix(*data)
    rows = {r['id']: r for r in result['rows']}
    assert len(rows) == 5  # two identities, one base-quality, two role-quality assignments
    named = rows['identity:u']
    assert named['dimensions']['named_tiers']['state'] == 'reviewed'
    for dim in ('desirability', 'leveling', 'market', 'report', 'stat_annotations'):
        assert named['dimensions'][dim]['state'] == 'pending'
    assert rows['identity:x']['dimensions']['discovery']['state'] == 'blocked'
    assert rows['base:base:normal']['dimensions']['socket_mechanics']['state'] == 'reviewed'
    assert rows['base:base:normal']['dimensions']['desirability']['state'] == 'pending'
    assert rows['use:role:magic']['dimensions']['desirability']['state'] == 'reviewed'
    assert rows['use:role:rare']['dimensions']['stat_annotations']['state'] == 'pending'
    assert result['complete'] is False
    assert result['counts']['by_kind'] == {'base_quality': 1, 'identity': 2, 'use_quality': 2}
    assert all(d['sources'] and d['reason'] for r in result['rows'] for d in r['dimensions'].values())
    changed = deepcopy(data)
    changed[2]['rows'][0]['source_error'] = 'stale source'
    blocked = build_matrix(*changed)
    assert (
        next(r for r in blocked['rows'] if r['id'] == 'identity:u')['dimensions']['named_tiers']['state'] == 'blocked'
    )


def test_matrix_rejects_lost_occurrence_identities_and_duplicate_rows():
    data = inputs()
    data[0]['occurrences'][0]['identity_id'] = 'missing'
    with pytest.raises(ValueError, match='identity'):
        build_matrix(*data)
    data = inputs()
    data[1]['rows'].append(deepcopy(data[1]['rows'][0]))
    with pytest.raises(ValueError, match='Duplicate'):
        build_matrix(*data)


def test_stale_source_snapshot_is_rejected(tmp_path):
    import hashlib

    from pricing.knowledge.assessment.maintenance.coverage_matrix import validate_inputs
    from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint

    source = tmp_path / 'guide'
    source.write_text('original')
    docs = {
        'inventory': {
            'input_hashes': {'guide': hashlib.sha256(source.read_bytes()).hexdigest()},
            'profile_fingerprint': fingerprint({'profiles': []}),
        },
        'bases': {'sources': {}},
        'profiles': {'profiles': []},
    }
    validate_inputs(docs, tmp_path)
    source.write_text('changed')
    with pytest.raises(ValueError, match='Stale'):
        validate_inputs(docs, tmp_path)


def test_observed_capture_gaps_enter_dimension_queues_without_valuation():
    from pricing.knowledge.assessment.maintenance.observed_review import merge_replays
    from tests.pricing.knowledge.assessment.maintenance.test_observed_review import replay

    observed = merge_replays({}, {'item': replay()}, {'capture.json': 'sha'})
    result = build_matrix(*inputs(), observed=observed)
    row = next(r for r in result['rows'] if r['kind'] == 'observed_capture')
    assert row['facts']['sockets'] is None
    for key in ('capture', 'market_mapping', 'desirability', 'market'):
        assert any(q['row_id'] == row['id'] for q in result['review_queues'][key])
    assert row['facts']['rarity'] not in ('unique', 'set')
    assert row['dimensions']['named_tiers']['state'] == 'excluded'
    assert not any(q['row_id'] == 'identity:u' for q in result['review_queues']['named_tiers'])


@pytest.mark.parametrize(
    ('qualities', 'state'),
    [
        (['normal', 'superior', 'magic', 'rare', 'crafted', 'low_quality'], 'excluded'),
        (['magic', 'unique'], 'pending'),
        (['normal', 'set'], 'pending'),
        (['magic', 'unknown'], 'pending'),
        ([], 'pending'),
    ],
)
def test_validated_collection_named_tier_applicability(monkeypatch, qualities, state):
    from pricing.knowledge.assessment.maintenance import pattern_collections

    # Source validation is exercised by the real collection tests. Here isolate
    # the matrix boundary: mixed or unknown qualities cannot lose named review.
    monkeypatch.setattr(
        pattern_collections,
        'compile_collections',
        lambda *args, **kwargs: {'x': {'qualities': qualities, 'reason': 'Reviewed members', 'review_index': 0}},
    )
    result = build_matrix(*inputs(), pattern_reviews={}, uses={'uses': []}, table_reviews={})
    row = next(row for row in result['rows'] if row['id'] == 'identity:x')
    assert row['dimensions']['named_tiers']['state'] == state
    for key in ('market', 'report', 'leveling', 'socket_mechanics', 'stat_annotations'):
        assert row['dimensions'][key]['state'] == 'pending'


@pytest.mark.parametrize(
    ('quality', 'state'),
    [
        ('magic', 'excluded'),
        ('rare', 'excluded'),
        ('crafted', 'excluded'),
        ('unique', 'pending'),
        ('set', 'pending'),
        (None, 'pending'),
        ('unknown', 'pending'),
    ],
)
def test_value_watch_named_tiers_follow_explicit_quality_without_closing_other_reviews(quality, state):
    watch = {
        'name': 'Grand Charm',
        'rarity': quality,
        'kind': 'affixed_value_watch',
        'details': {'priority': 'valuable_candidate'},
    }
    result = build_matrix(*inputs(), valuable={'rows': [watch]})
    row = next(r for r in result['rows'] if r['id'] == 'evidence:valuable:rows:0')
    assert row['dimensions']['named_tiers']['state'] == state
    assert row['evidence'] == watch
    assert row['dimensions']['discovery']['state'] == 'blocked'
    for key in ('desirability', 'market', 'report', 'leveling', 'socket_mechanics', 'stat_annotations'):
        assert row['dimensions'][key]['state'] == 'pending'


def test_build_utility_and_named_tiers_do_not_establish_trade_qualification():
    result = build_matrix(*inputs())
    rows = {r['id']: r for r in result['rows']}
    assert rows['identity:u']['dimensions']['named_tiers']['state'] == 'reviewed'
    assert rows['use:role:magic']['dimensions']['desirability']['state'] == 'reviewed'
    for key in ('identity:u', 'base:base:normal', 'use:role:magic', 'use:role:rare'):
        assert rows[key]['dimensions']['trade_qualification']['state'] == 'pending'
