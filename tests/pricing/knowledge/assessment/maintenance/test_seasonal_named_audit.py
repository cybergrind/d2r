"""Seasonal overlays must not erase ordinary named-item evidence."""

from pricing.knowledge.assessment.maintenance.seasonal_named_audit import audit


def test_same_table_id_preserves_both_versions_and_property_difference():
    ordinary = {'*ID': 121, 'index': 'Manald Heal', 'code': 'rin', 'prop1': 'hp', 'min1': 20, 'max1': 20}
    seasonal = {**ordinary, 'firstLadderSeason': 15, 'lastLadderSeason': 15, 'prop2': 'cast2', 'min2': 10, 'max2': 10}
    result = audit({'121': ordinary}, {'121': seasonal})
    assert len(result) == 1
    row = result[0]
    assert row['ordinary'] == ordinary
    assert row['seasonal'] == seasonal
    assert row['differences']['prop2'] == {
        'ordinary_present': False,
        'seasonal_present': True,
        'ordinary': None,
        'seasonal': 'cast2',
    }
    assert row['state'] == 'requires_variant_support'


def test_existing_season_flag_without_definition_change_is_not_an_overlay_conflict():
    ordinary = {'*ID': 401, 'index': 'Cold Rupture', 'firstLadderSeason': 2}
    assert audit({'401': ordinary}, {'401': ordinary}) == []


def test_missing_ordinary_record_is_explicit_and_not_synthesized():
    seasonal = {'*ID': 121, 'index': 'Manald Heal', 'firstLadderSeason': 15}
    row = audit({}, {'121': seasonal})[0]
    assert row['state'] == 'ordinary_definition_missing'
    assert row['ordinary'] is None


def test_identity_collision_is_not_treated_as_a_reviewed_variant():
    row = audit({'1': {'*ID': 1, 'index': 'Different'}}, {'1': {'*ID': 1, 'index': 'New', 'firstLadderSeason': 15}})[0]
    assert row['state'] == 'identity_conflict'


def test_chronicle_restriction_is_not_a_stat_variant():
    ordinary = {'*ID': 401, 'index': 'Cold Rupture', 'firstLadderSeason': 2}
    row = audit({'401': ordinary}, {'401': {**ordinary, 'disableChronicle': 1}})[0]
    assert row['state'] == 'requires_mode_review'
