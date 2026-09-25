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
