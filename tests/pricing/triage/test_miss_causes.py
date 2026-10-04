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
