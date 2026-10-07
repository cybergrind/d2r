import pytest

from pricing.triage.engine import assess, prepare_tables
from pricing.triage.named_roll_placement import compile_placements
from tests.pricing.triage.test_bands import listing


POLICY = {
    'category': 'uniques',
    'name': 'Shaftstop',
    'conditions': {'ethereal': False, 'base_code': 'xhn', 'sockets': 0, 'socket_contents': 'empty'},
    'property': '425',
    'label': 'Enhanced Defense',
    'min': 180,
    'max': 220,
    'valuable_min': 218,
    'source': 'guides/pricing.html#shaftstop-roll-review',
    'alternative': 'ethereal or 218%+ copies',
}


def setup():
    rows = [
        listing(i, price)
        | {
            'name': 'Shaftstop',
            'ethereal': False,
            'base_code': 'xhn',
            'sockets': 0,
            'socket_contents': 'empty',
            'properties': {**listing(i)['properties'], '425': roll},
        }
        for i, (roll, price) in enumerate([(183, 0.5), (197, 0.6), (215, 1), (218, 4), (219, 5), (220, 8)])
    ]
    placements = compile_placements(rows, [POLICY])
    return prepare_tables(
        {'bands': [], 'named_roll_placements': placements}, {'keep_ist': 0.25, 'rows': []}, {'rows': []}
    )


def item(roll=197, **fields):
    return {
        'category': 'uniques',
        'name': 'Shaftstop',
        'ethereal': False,
        'base_code': 'xhn',
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {'425': roll},
        **fields,
    }


def test_ordinary_shaftstop_does_not_inherit_name_demand_or_top_price():
    tables = setup()
    tables['demand'] = {'uniques/shaftstop': [{'ethereal': None, 'build': 'example'}]}
    result = assess(item(), tables)
    assert result['verdict'] == 'vendor'
    assert '197' in result['reason']
    assert '180-220' in result['reason']
    assert '218' in result['reason']
    assert result['decision_ist'] < 1
    from inventory_tracking.appraisal.triage import headline

    assert 'ordinary roll' in headline(result)


def test_top_shaftstop_uses_only_top_group_prices():
    result = assess(item(220), setup())
    assert result['verdict'] == 'slow'
    assert result['decision_ist'] >= 4
    assert result['band']['sellers'] == 3
    from inventory_tracking.appraisal.triage import headline

    assert '220' in headline(result)
    assert '218' in headline(result)


@pytest.mark.parametrize('fields', [{'ethereal': True}, {'base_code': 'uhn'}, {'sockets': 1}, {'base_code': None}])
def test_roll_policy_cannot_cross_variants(fields):
    assert assess(item(**fields), setup())['roll_placement'] is None


@pytest.mark.parametrize('roll', [None, 179, 221])
def test_missing_or_impossible_roll_does_not_get_top_or_ordinary_verdict(roll):
    assert assess(item(roll), setup())['verdict'] == 'check'


def test_saved_shaftstops_use_reviewed_roll_group_and_no_unqualified_watch():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.policies.value_watch import matching_watches
    from pricing.triage.adapters import from_drop
    from pricing.triage.engine import Tables

    captures = [
        json.loads(line) for line in Path('inventory_tracking/corpus/data/items.jsonl').read_text().splitlines()
    ]
    watches = json.loads(Path('pricing/data/appraisal-value-watch.json').read_text())['rows']
    watches = [r for r in watches if r['name'] == 'Shaftstop']
    tables = Tables().load()
    for ident in ('6d727fb43b0c', '756258ce7ad2', 'bd60b11d0216'):
        observation = next(r['observation'] for r in captures if r['id'] == ident)
        result = assess(from_drop(observation), tables)
        assert result['verdict'] == 'vendor'
        assert result['roll_placement']['group'] == 'ordinary'
        assert not matching_watches(watches, normalize(observation))


def test_only_roll_group_demand_can_rescue_an_ordinary_copy():
    from pricing.triage.named_roll_placement import ordinary_has_demand

    placement = assess(item(), setup())['roll_placement']
    key = placement['band']['bucket']
    assert not ordinary_has_demand(placement, {'buyers': 5, 'uncensored_disappeared': 10})
    assert not ordinary_has_demand(placement, {'roll_groups': {key: {'disappeared': 5}}})
    assert ordinary_has_demand(placement, {'roll_groups': {key: {'buyers': 1}}})
    assert ordinary_has_demand(placement, {'roll_groups': {key: {'uncensored_disappeared': 1}}})


def test_roll_groups_cannot_be_created_by_duplicate_sellers():
    rows = [
        listing(i, price)
        | {
            'name': 'Shaftstop',
            'ethereal': False,
            'base_code': 'xhn',
            'sockets': 0,
            'socket_contents': 'empty',
            'properties': {**listing(i)['properties'], '425': roll},
        }
        for i, (roll, price) in enumerate([(190, 0.5), (197, 0.6), (215, 1), (220, 8)])
    ]
    rows.extend(rows[-1] | {'listing_id': f'copy-{i}'} for i in range(20))
    assert compile_placements(rows, [POLICY]) == []


def test_scoped_ordinary_buyers_restore_slow_sale_in_engine():
    from pricing.triage.listing_scores import cohort_key

    tables = setup()
    result = assess(item(), tables)
    group = result['band']['bucket']
    key = cohort_key(item(), result, None, tables)
    tables['market_demand'] = {
        'complete': True,
        'buyers': {},
        'cohorts': {key: {'previous_listings': 8, 'current_listings': 8, 'roll_groups': {group: {'buyers': 1}}}},
    }
    assert assess(item(), tables)['verdict'] == 'slow'
