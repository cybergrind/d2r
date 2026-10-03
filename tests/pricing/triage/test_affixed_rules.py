from pricing.triage.engine import assess
from pricing.triage.import_affixed_rules import affixed_rules


def verdict(family, properties, category='rare'):
    return assess(
        {'category': category, 'family': family, 'name': 'Example', 'properties': properties},
        {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': affixed_rules()}, 'own': {'rows': []}},
    )['verdict']


def test_caster_ring_needs_both_mandatory_and_supporting_stats():
    assert verdict('ring', {'520': 10, '418': 30, '427': 20}) == 'check'
    assert verdict('ring', {'520': 10, '427': 20, '428': 20}) == 'vendor'
    assert verdict('ring', {'418': 30, '427': 20}) == 'vendor'


def test_circlet_and_craft_do_not_borrow_other_slots_rules():
    assert verdict('circ', {'1862': 2, '520': 20}, 'magic') == 'check'
    assert verdict('circ', {'1862': 2, '520': 10}, 'magic') == 'vendor'
    assert verdict('amul', {'1862': 2, '520': 20}, 'crafted') == 'check'
    assert verdict('ring', {'1862': 2, '520': 20}, 'crafted') == 'vendor'


def test_boots_require_speed_and_two_high_resistances():
    assert verdict('boot', {'480': 30, '427': 30, '428': 25}) == 'check'
    assert verdict('boot', {'480': 30, '427': 30, '428': 24}) == 'vendor'
    assert verdict('boot', {'427': 30, '428': 30}) == 'vendor'
