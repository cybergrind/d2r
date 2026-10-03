from pricing.triage.engine import matches


def test_two_support_groups_not_two_resistances_from_one_all_resist_roll():
    rule = {
        'properties': {'520': {'min': 10}},
        'at_least': {
            'count': 2,
            'of': [
                {
                    'at_least': {
                        'count': 1,
                        'of': [{'properties': {p: {'min': 10}}} for p in ('427', '428', '426', '401')],
                    }
                },
                {'properties': {'418': {'min': 1}}},
                {'properties': {'437': {'min': 1}}},
            ],
        },
    }
    props = {'520': 10, '427': 15, '428': 15, '426': 15, '401': 15}
    assert not matches({'properties': props}, rule)
    assert matches({'properties': props | {'418': 30}}, rule)
    assert not matches({'properties': props | {'418': 30, '520': 0}}, rule)


def test_malformed_or_duplicate_supports_cannot_create_a_paid_combination():
    support = {'properties': {'418': {'min': 1}}}
    for group in (
        {'count': 2, 'of': [support, support]},
        {'count': 0, 'of': [support]},
        {'count': True, 'of': [support]},
        {'count': 1, 'of': [{}]},
    ):
        assert not matches({'properties': {'418': 40}}, {'at_least': group})
