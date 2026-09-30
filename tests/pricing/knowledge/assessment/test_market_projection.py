from pricing.knowledge.assessment.adapters.capture import normalize
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def extraction(stats, affixes=()):
    item = facts('Demon Heart', 'rare', 'Storm Gyre').to_dict()
    item['affixes'] = list(affixes)
    return {
        'item': item,
        'source': {'stat_capture_complete': True},
        'decoded_stats': [
            {
                'memory_stat': {'id': stat, 'layer': layer, 'raw': raw},
                'status': 'decoded',
                'value': value,
                'text': 'arbitrary display',
            }
            for stat, layer, raw, value in stats
        ],
    }


def test_parameterized_skill_and_flee_properties_use_native_identity():
    result = normalize(extraction([(188, 9, 2, 2), (107, 56, 1, 1), (112, 0, 128, 100)]))
    assert result.properties == {'516': 2, '943': 1, '534': 100}
    assert not result.projection_gaps
    assert result.stats['107:56']['market_property'] == '943'


def test_projection_never_uses_other_skill_parameter_or_undecoded_value():
    data = extraction([(188, 10, 1, 1), (107, 9999, 1, 1), (112, 1, 128, 100)])
    result = normalize(data)
    assert result.properties == {'517': 1}
    assert len(result.projection_gaps) == 2
    data['decoded_stats'][0]['status'] = 'unresolved'
    assert '517' not in normalize(data).properties


def test_conflicting_existing_projection_is_not_silently_overwritten():
    data = extraction(
        [(188, 9, 2, 2)], [{'property_id': '516', 'value': 3, 'memory_stat': {'id': 188, 'layer': 9, 'raw': 2}}]
    )
    result = normalize(data)
    assert any('conflict' in gap.lower() for gap in result.gaps)


def test_class_aura_and_oskill_are_distinct_market_properties():
    result = normalize(extraction([(83, 3, 1, 1), (151, 120, 12, 12), (97, 9, 5, 5)]))
    assert result.properties == {'442': 1, '859': 12, '1210': 5}


def test_compiled_skill_catalog_projects_class_tree_and_staffmod_independently():
    result = normalize(extraction([(83, 2, 2, 2), (83, 7, 2, 2), (188, 8, 3, 3), (107, 274, 2, 2)]))
    assert result.properties == {'498': 2, '1862': 2, '515': 3, '1075': 2}
    assert not result.projection_gaps


def test_projection_compiler_refuses_ambiguous_market_labels():
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.maintenance.market_projection import compile_projection

    properties = {
        'first': {'labels': ['+{{value}} to Necromancer Skill Levels'], 'types': ['number']},
        'second': {'labels': ['+{{value}} to Necromancer Skill Levels'], 'types': ['number']},
    }
    result = compile_projection(metadata(), properties)
    assert '83:2' not in result['mappings']
    assert result['unmapped']['83:2']['reason'] == 'ambiguous market label'


def test_magic_pierce_uses_verified_numeric_market_field_and_preserves_roll():
    import json
    from pathlib import Path

    properties = json.loads(Path('pricing/data/appraisal-properties.json').read_text())['properties']
    assert properties['1877']['labels'] == ['-{{value}}% to Enemy Magic Resistance']
    assert properties['1877']['types'] == ['number']
    for roll in (3, 5, 8):
        result = normalize(extraction([(358, 0, roll, roll)]))
        assert result.properties == {'1877': roll}
        assert result.stats['358:0']['market_property'] == '1877'
        assert not result.projection_gaps


def test_magic_pierce_mapping_rejects_other_parameters_unresolved_and_conflicts():
    data = extraction([(358, 1, 5, 5)])
    assert '1877' not in normalize(data).properties
    data = extraction([(358, 0, 5, 5)])
    data['decoded_stats'][0]['status'] = 'unresolved'
    assert '1877' not in normalize(data).properties
    data = extraction(
        [(358, 0, 5, 5)], [{'property_id': '1877', 'value': 3, 'memory_stat': {'id': 358, 'layer': 0, 'raw': 3}}]
    )
    result = normalize(data)
    assert '1877' not in result.properties
    assert any('conflict' in gap.lower() for gap in result.gaps)


def test_complete_native_sling_can_form_exact_named_contract():
    from pricing.knowledge.assessment.handlers.named import NamedHandler
    from tests.pricing.knowledge.assessment.item_bank.cases.echoing_sling import RING

    item = normalize(RING.capture())
    contract, gaps = NamedHandler().contract(item, 'ring')
    assert contract is not None, gaps
    assert contract.to_dict()['properties']['1877'] == 3
    assert not gaps


def test_town_portal_oskill_mapping_is_specific_to_native_identity():
    import json
    from pathlib import Path

    properties = json.loads(Path('pricing/data/appraisal-properties.json').read_text())['properties']
    assert properties['1878']['labels'] == ['+{{value}} to Town Portal']
    assert properties['1878']['types'] == ['number']
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.maintenance.market_projection import compile_projection

    compiled = compile_projection(metadata(), properties)
    assert compiled['mappings']['97:411']['property_id'] == '1878'
    assert compiled['mappings']['97:411']['native_label'] == '+{{value}} to Town Portal'
    native = json.loads(Path('third-parties/d2data/json/uniqueitems.json').read_text())['415']
    assert (native['prop1'], native['par1'], native['min1'], native['max1']) == ('oskill', 'Townportal O Skill', 1, 1)
    result = normalize(extraction([(97, 411, 1, 1)]))
    assert result.properties == {'1878': 1}
    for stat in (107, 151, 204):
        assert '1878' not in normalize(extraction([(stat, 411, 1, 1)])).properties


def test_sling_comparison_does_not_mix_magic_pierce_rolls():
    from pricing.knowledge.assessment.comparables import evaluate
    from pricing.knowledge.assessment.handlers.named import NamedHandler
    from tests.pricing.knowledge.assessment.item_bank.cases.echoing_sling import RING
    from tests.pricing.knowledge.assessment.test_comparables import listing

    contract, gaps = NamedHandler().contract(normalize(RING.capture()), 'ring')
    assert contract is not None, gaps
    data = contract.to_dict()
    candidate = listing(
        name='Sling',
        rarity='unique',
        sockets=0,
        socket_contents='empty',
        base_code=data['base_code'],
        properties=data['properties'],
    )
    result = evaluate(
        data,
        [
            candidate,
            {
                **candidate,
                'seller_id': 'other',
                'listing_id': 'other',
                'properties': {**candidate['properties'], '1877': 5},
            },
        ],
    )
    assert result['summary']['priced_sellers'] == 1
    assert len(result['rejected']) == 1
    assert result['rejected'][0]['reasons']
