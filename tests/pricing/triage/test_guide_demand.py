from pricing.triage.demand import demand_for
from pricing.triage.engine import assess, prepare_tables
from pricing.triage.guide_demand import compile_cases


def test_guide_listed_sub_ist_base_is_demand_only_for_recorded_variant():
    item = {
        'category': 'base',
        'name': 'Thresher',
        'ethereal': True,
        'sockets': 4,
        'socket_contents': 'empty',
        'rarity': 'normal',
        'base_code': '7s8',
        'properties': {},
    }
    cases = [
        {
            'id': 'guide#base',
            'kind': 'table',
            'classification': 'verdict',
            'examples': [{'item': item, 'expected': ['sell', 'slow']}],
        }
    ]
    evidence = compile_cases(cases)
    assert demand_for(item, evidence)
    assert not demand_for(item | {'ethereal': False}, evidence)
    assert not demand_for(item | {'sockets': 3}, evidence)
    band = {
        'category': 'base',
        'name': 'Thresher',
        'bucket': 'name',
        'q1_ist': 0.5,
        'median_ist': 0.6,
        'sellers': 10,
        'liquidity': 'liquid',
    }
    tables = prepare_tables({'bands': [band], 'demand': evidence}, {'keep_ist': 0.25, 'rows': []}, {'rows': []})
    from pricing.triage.listing_scores import cohort_key

    result = assess(item, tables)
    key = cohort_key(item, result, None, tables)
    tables['market_demand'] = {
        'complete': True,
        'buyers': {},
        'cohorts': {key: {'previous_listings': 10, 'current_listings': 10, 'maximum_interval_hours': 168}},
    }
    assert assess(item, tables)['verdict'] == 'slow'


def test_vendor_and_check_only_guide_examples_do_not_create_sale_demand():
    item = {'category': 'uniques', 'name': 'Example', 'ethereal': True, 'properties': {'425': 220}}
    assert not compile_cases([{'id': 'negative', 'kind': 'table', 'item': item, 'expected': ['vendor', 'check']}])
    evidence = compile_cases([{'id': 'positive', 'kind': 'table', 'item': item, 'expected': ['slow']}])
    assert demand_for(item, evidence)
    assert not demand_for(item | {'properties': {'425': 197}}, evidence)
