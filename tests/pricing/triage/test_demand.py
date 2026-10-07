from pricing.triage.demand import compile_demand, demand_for
from pricing.triage.engine import assess
from tests.pricing.triage.test_bands import listing
from tests.pricing.triage.test_named_bands import tables


def mention(variant='Standard', **fields):
    return {
        'name': 'Example',
        'category': 'unique',
        'variant': variant,
        'build': 'build-a',
        'source_id': 'pricing/data/wp-a-builds.json',
        'source_locator': '/build-a/variants/1/player/Helmet/0',
        'side': 'player',
        'slot': 'Helmet',
        'original_label': 'Example',
        'details': {'recommended': True, 'resolution_status': 'resolved'},
        **fields,
    }


def test_demand_requires_explicit_endgame_variant_and_preserves_merc_ethereal_requirement():
    for variant in ('Starter', 'Budget', 'Hardcore', 'Leveling', 'Guide mention'):
        assert compile_demand([mention(variant)]) == {}
    assert compile_demand([mention(details={'recommended': False})]) == {}
    assert compile_demand([mention(source_locator='/build-a/slots/Helmets/0')])
    evidence = compile_demand([mention('Ubers', side='merc', original_label='Example (ethereal)')])
    assert demand_for({'name': 'Example', 'category': 'uniques', 'ethereal': True}, evidence)
    assert not demand_for({'name': 'Example', 'category': 'uniques', 'ethereal': False}, evidence)
    assert not demand_for({'name': 'Example', 'category': 'sets', 'ethereal': True}, evidence)


def test_sub_ist_named_sell_requires_demand_but_keeps_ask_band():
    data = tables([listing(i, 0.6, ethereal=False) for i in range(10)])
    item = {'name': 'Example', 'category': 'uniques', 'ethereal': False}
    result = assess(item, data)
    assert result['verdict'] == 'slow'
    assert result['decision_ist'] == 0.6
    assert result['reason'] == 'demand unmeasured'
    data['demand'] = compile_demand([mention()])
    assert assess(item, data)['verdict'] == 'slow'
    # Demand does not establish a price, and cannot rescue a below-threshold item.
    assert assess(item, tables([]) | {'demand': data['demand']})['verdict'] != 'sell'
    cheap = tables([listing(i, 0.1, ethereal=False) for i in range(10)]) | {'demand': data['demand']}
    assert assess(item, cheap)['verdict'] == 'vendor'
    assert assess(item, tables([listing(i, 1, ethereal=False) for i in range(10)]))['verdict'] == 'sell'


def test_watch_and_socket_demand_union_excludes_floor_only():
    watches = [
        {'name': 'Facet', 'rarity': 'unique', 'details': {'priority': 'valuable_candidate'}},
        {'name': 'Useful', 'rarity': 'set', 'details': {'local_tier': 'Low'}},
        {'name': 'Floor', 'rarity': 'unique', 'details': {'local_tier': 'Floor'}},
        {'name': 'Insert', 'rarity': 'unique', 'details': {}},
    ]
    evidence = compile_demand(
        [mention(side='merc', category='magic', original_label='Example (ethereal; Insert socketed)')], watches
    )
    assert 'uniques/facet' in evidence
    assert 'sets/useful' in evidence
    assert 'uniques/floor' not in evidence
    assert demand_for({'name': 'Insert', 'category': 'uniques', 'ethereal': False}, evidence)


def test_unqualified_value_watch_is_not_variant_demand():
    watches = [
        {
            'name': 'Example',
            'rarity': 'unique',
            'details': {
                'priority': 'valuable_candidate',
                'guide_conditions': 'Medium Value in Hardcore; ethereal mercenary use',
            },
        }
    ]
    evidence = compile_demand([mention('Ubers', side='merc', original_label='Example (ethereal)')], watches)
    assert not demand_for({'name': 'Example', 'category': 'uniques', 'ethereal': False}, evidence)
    assert demand_for({'name': 'Example', 'category': 'uniques', 'ethereal': True}, evidence)


def test_supported_sale_precedes_own_use_without_losing_the_note():
    item = {'name': 'Example', 'category': 'uniques', 'ethereal': False}
    data = tables([listing(i, 0.6, ethereal=False) for i in range(10)])
    data['own'] = {'rows': [{'name': 'Example', 'label': 'Own charm'}]}
    result = assess(item, data)
    assert result['verdict'] == 'slow'
    assert result['decision_ist'] == 0.6
    assert result['own_use']['label'] == 'Own charm'
    from inventory_tracking.appraisal.triage import headline

    assert 'asks 0.6 Ist' in headline(result)
    assert 'Own use: Own charm' in headline(result)
    data['demand'] = compile_demand([mention()])
    assert assess(item, data)['verdict'] == 'slow'


def test_no_demand_review_list_uses_supported_leaf_cohorts():
    from pricing.triage.demand import cohorts_without_demand

    data = tables([listing(i, 0.6, ethereal=False) for i in range(10)])
    rows = cohorts_without_demand(data)
    assert len(rows) == 1
    assert rows[0]['q1_ist'] == 0.6
    assert rows[0]['ethereal'] is False
    assert cohorts_without_demand(data | {'demand': compile_demand([mention()])}) == []
    assert cohorts_without_demand(tables([listing(i, 0.6, ethereal=False) for i in range(9)])) == []


def test_recommended_build_lists_are_demand_and_keep_ethereal_variant():
    rows = [mention('Main alternatives', source_locator='/build-a/slots/Helmet/0', original_label='Example (ethereal)')]
    evidence = compile_demand(rows)
    assert demand_for({'name': 'Example', 'category': 'uniques', 'ethereal': True}, evidence)
    assert not demand_for({'name': 'Example', 'category': 'uniques', 'ethereal': False}, evidence)
