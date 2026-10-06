import pytest

from pricing.triage.miss_causes import cause


@pytest.mark.parametrize(
    ('fields', 'expected'),
    [
        ({'socket_contents': 'filled'}, 'base_socket_contents_filled'),
        ({'socket_contents': None}, 'base_socket_contents_missing'),
        ({'base_ed': None}, 'base_enhancement_missing'),
        ({'base_ed': 700}, 'base_enhancement_invalid'),
        ({'base_ed': -1}, 'base_enhancement_invalid'),
        ({'rarity': 'normal'}, 'base_quality_conflicting'),
        ({'ethereal': None}, 'base_ethereal_missing'),
        ({'base_modifiers': None}, 'base_modifiers_unreadable'),
        ({}, 'base_bucket_missing'),
    ],
)
def test_base_rule_gap_is_separate_from_missing_or_conflicting_evidence(fields, expected):
    item = {
        'category': 'base',
        'rarity': 'superior',
        'socket_contents': 'empty',
        'ethereal': False,
        'base_ed': 15,
        'base_modifiers': {},
        **fields,
    }
    result = {'verdict': 'vendor', 'band': None}
    assert cause(item, result, {'rules': {'rows': []}}) == expected


def test_affixed_signature_is_not_reported_as_a_missing_clean_base_bucket():
    from pricing.triage.guide_cases import item_from_spec

    item = item_from_spec(
        {
            'base': 'Circlet',
            'rarity': 'superior',
            'ethereal': False,
            'sockets': 2,
            'stats': {'16:0': 15, '105:0': 20, '83:1': 2},
        }
    )
    result = {'verdict': 'vendor', 'band': None}
    assert cause(item, result, {'rules': {'rows': []}}) == 'base_native_modifiers_conflicting'
    plain = item_from_spec(
        {
            'base': 'Circlet',
            'rarity': 'superior',
            'ethereal': False,
            'sockets': 2,
            'stats': {'16:0': 15},
        }
    )
    assert cause(plain, result, {'rules': {'rows': []}}) == 'base_bucket_missing'


def test_self_use_with_a_price_band_is_not_mislabeled_below_keep_price():
    result = {'verdict': 'self', 'band': {'q1_ist': 2, 'sellers': 5}}
    assert cause({'category': 'base'}, result, {}) == 'own_use_only'
