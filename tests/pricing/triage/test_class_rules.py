from pricing.triage.engine import assess
from pricing.triage.import_class_rules import class_rules


def verdict(family, properties, category='magic', **fields):
    fields.setdefault('base_name', 'Stilleto')
    return assess(
        {'category': category, 'family': family, 'name': 'Test', 'properties': properties, **fields},
        {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': class_rules()}, 'own': {'rows': []}},
    )


def test_unpaid_stiletto_staffmods_do_not_trigger_check():
    result = verdict('knif', {'1561': 1, '1574': 3}, sockets=0)
    assert result['verdict'] == 'vendor'
    assert 'staffmods alone' in result['reason']


def test_paid_dagger_needs_class_skill_paid_staffmod_and_support():
    assert verdict('knif', {'1862': 2, '1565': 3, '457': 20})['verdict'] == 'check'
    for props in ({'1862': 2, '1565': 3}, {'1565': 3, '457': 20}, {'1862': 2, '1574': 3, '457': 20}):
        assert verdict('knif', props)['verdict'] == 'vendor'


def test_necro_head_and_barbarian_helm_require_paid_combinations():
    assert verdict('head', {'498': 2, '1024': 3, '449': 20}, 'rare')['verdict'] == 'check'
    assert verdict('head', {'498': 2, '1024': 3}, 'rare')['verdict'] == 'vendor'
    assert verdict('phlm', {'403': 2, '765': 3}, 'rare')['verdict'] == 'check'
    assert verdict('phlm', {'403': 2, '765': 2}, 'rare')['verdict'] == 'vendor'


def test_class_rule_does_not_apply_to_generic_weapon_or_different_rarity():
    props = {'1862': 2, '1565': 3, '457': 20}
    assert verdict('axe', props)['verdict'] == 'vendor'
    assert verdict('knif', props, 'unique')['verdict'] == 'vendor'


def test_paid_dagger_still_needs_an_allowed_base_line():
    props = {'1862': 2, '1565': 3, '457': 20}
    assert verdict('knif', props, base_name='Dirk')['verdict'] == 'vendor'
    assert verdict('knif', props, base_name=None)['verdict'] == 'vendor'


def test_orb_cast_rate_does_not_accept_an_unrelated_skill_tree():
    assert verdict('orb', {'514': 2, '520': 20})['verdict'] == 'check'
    assert verdict('orb', {'514': 2, '486': 20})['verdict'] == 'vendor'


def test_listing_replay_reports_paid_checks_without_counting_them_as_sales():
    from pricing.triage.replay import listing_score
    from tests.pricing.triage.test_bands import listing

    row = listing(1)
    row.update(name='Bone Knife', category='base', rarity='magic')
    row['properties'].update({'1862': 2, '1565': 3, '457': 20})
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': class_rules()}, 'own': {'rows': []}}
    score = listing_score([row], tables)['categories']['magic']
    assert score['checks_valuable'] == 1
    assert score['flagged_valuable'] == 0
