from pricing.knowledge.assessment.adapters.capture import normalize
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def capture(values):
    return {
        'item': facts('Jewel', 'magic').to_dict(),
        'source': {'stat_capture_complete': True},
        'decoded_stats': [
            {'status': 'decoded', 'value': value, 'memory_stat': {'id': stat, 'layer': 0, 'raw': value}}
            for stat, value in values.items()
        ],
    }


def test_lightning_facet_components_keep_damage_endpoints_and_rolls_distinct():
    item = normalize(capture({50: 1, 51: 74, 330: 5, 334: 4}))
    assert item.properties == {'478': 1, '479': 74, '743': 5, '736': 4}
    assert not item.projection_gaps


def test_cold_projection_does_not_discard_unmapped_duration():
    item = normalize(capture({54: 24, 55: 38, 56: 75, 331: 5, 335: 3}))
    assert item.properties == {'482': 24, '483': 38, '747': 5, '609': 3}
    assert item.projection_gaps == ('No verified market mapping for native stat 56:0.',)


def test_fire_and_poison_masteries_do_not_turn_into_poison_damage():
    item = normalize(capture({48: 17, 49: 45, 329: 3, 333: 5, 332: 4, 336: 5}))
    assert item.properties == {'458': 17, '459': 45, '750': 3, '735': 5, '783': 4, '723': 5}
    assert not item.projection_gaps
