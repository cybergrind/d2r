from copy import deepcopy

from inventory_tracking.appraisal.build_use_summary import build_use_summary


def role(i, **changes):
    return {
        'id': str(i),
        'build': f'build-{i}',
        'variant': 'Starter',
        'side': 'merc',
        'slot': 'Weapon',
        'role': 'Mana support',
        'status': 'partial',
        'missing': ['Mercenary type unknown'],
        'failed': [],
        'alternatives': ['Exceptional base'],
        'dependencies': [],
        'preferences': [{'label': 'Level 17 Meditation', 'status': 'false'}],
        **changes,
    }


def test_summary_budget_preserves_all_details_and_deduplicates_targets():
    roles = [role(i) for i in range(10)]
    saved = deepcopy(roles)
    summary = build_use_summary(roles, {'grade': 'Pending', 'distinct_builds': 5, 'complete': False})
    assert len(summary.lines) <= 8
    assert len(summary.details) == 10
    assert len(summary.clusters) == 1
    assert sum('Level 17 Meditation' in line for line in summary.lines) == 1
    assert '+7 more' in '\n'.join(summary.lines)
    assert '0 more groups' not in '\n'.join(summary.lines)
    assert 'at least 5 builds' in summary.lines[0]
    assert roles == saved
    assert summary == build_use_summary(
        list(reversed(roles)), {'grade': 'Pending', 'distinct_builds': 5, 'complete': False}
    )


def test_base_dependencies_beneficiaries_and_failures_are_not_hidden_by_top_three():
    roles = [
        role(1, status='matched'),
        role(2, side='player'),
        role(3, alternatives=['Elite base']),
        role(4, dependencies=[{'label': 'Cure'}]),
        role(5, status='failed', failed=['Wrong base']),
    ]
    summary = build_use_summary(roles)
    assert len(summary.clusters) == 5
    assert any('1 failed' in line for line in summary.lines)
    assert any('2 more groups' in line for line in summary.lines)
    assert len(summary.details) == 5
    assert len(summary.lines) <= 8


def test_duplicate_evidence_does_not_change_summary_and_empty_roles_have_no_section():
    roles = [role(1)]
    assert build_use_summary(roles) == build_use_summary(roles + roles)
    assert build_use_summary([]).lines == ()


def test_omitted_failure_reason_survives_and_build_labels_are_readable():
    roles = [role(i, build=f'example-{i}-build-guide') for i in range(4)]
    roles.append(role(9, status='failed', failed=['Requires an elite polearm']))
    summary = build_use_summary(roles)
    assert 'Requires an elite polearm' in '\n'.join(summary.lines)
    assert 'Example 0' in '\n'.join(summary.lines)
    assert 'example-0-build-guide' not in '\n'.join(summary.lines)


def test_full_details_keep_source_and_failed_requirements():
    from inventory_tracking.appraisal.build_use_summary import detail_lines

    summary = build_use_summary(
        [role(1, failed=['Wrong base'], status='failed', source={'path': 'guide.json', 'locator': '/variants/1'})]
    )
    text = '\n'.join(detail_lines(summary))
    assert 'Wrong base' in text
    assert 'guide.json /variants/1' in text
    assert 'Exceptional base' in text


def test_full_details_render_dependencies_even_for_omitted_groups():
    from inventory_tracking.appraisal.build_use_summary import detail_lines

    roles = [role(i, status='matched', role=f'Use {i}') for i in range(3)]
    roles.append(
        role(
            9,
            dependencies=[
                {'label': 'Enigma must not be equipped', 'status': 'false'},
                {'label': 'Bramble equipped', 'status': 'true'},
                {'label': 'Mercenary has Infinity', 'status': 'unknown'},
            ],
        )
    )
    summary = build_use_summary(roles)
    assert 'Enigma must not be equipped' not in '\n'.join(summary.lines)
    text = '\n'.join(detail_lines(summary))
    assert 'Needs: Enigma must not be equipped' in text
    assert 'Setup: Bramble equipped' in text
    assert 'Check: Mercenary has Infinity' in text


def test_shared_presentation_uses_bounded_summary_for_terminal_and_osd():
    from inventory_tracking.appraisal.presentation import ItemAssessment

    record = {
        'request_id': 'test',
        'state': 'complete',
        'result': {
            'extraction': {'item': {'name': 'Insight', 'rarity': 'normal'}, 'decoded_stats': [], 'issues': []},
            'assessment': {'roles': [role(i) for i in range(10)]},
            'decision': {},
        },
    }
    presentation = ItemAssessment.from_record(record)
    terminal = [line.text for line in presentation.lines]
    osd = [line.text for line in presentation.to_osd()]
    summary = build_use_summary(record['result']['assessment']['roles'])
    assert all(line in terminal and line in osd for line in summary.lines)
    assert len(summary.lines) <= 8


def test_reviewed_progression_groups_equivalent_variants_but_preserves_rule_boundaries():
    roles = [
        role(1, variant='Standard'),
        role(2, variant='Magic Find'),
        role(3, variant='Starter'),
        role(4, variant='Magic Find', rule_trace={'value': 99}),
    ]
    demand = {
        'grade': 'Pending',
        'distinct_builds': 4,
        'role_presentation': {
            '1': {'progression': 'Endgame'},
            '2': {'progression': 'Endgame'},
            '3': {'progression': 'Starter'},
            '4': {'progression': 'Endgame'},
        },
    }
    summary = build_use_summary(roles, demand)
    assert len(summary.clusters) == 3
    assert {r['variant'] for r in next(g for g in summary.clusters if len(g) == 2)} == {'Standard', 'Magic Find'}
    assert 'Starter' in summary.lines[2]
    assert len(summary.details) == 4


def test_unknown_owner_classes_do_not_split_equivalent_mercenary_uses():
    def trace(class_name):
        return {
            'truth': 'unknown',
            'reason': 'all',
            'children': [
                {
                    'truth': 'unknown',
                    'reason': f'player_class: {class_name}',
                    'observed': None,
                    'expected': class_name,
                    'children': [],
                },
                {'truth': 'true', 'reason': 'base_code: xlt', 'observed': 'xlt', 'expected': 'xlt', 'children': []},
            ],
        }

    roles = [role(1, rule_trace=trace('Warlock')), role(2, rule_trace=trace('Paladin'))]
    saved = deepcopy(roles)
    summary = build_use_summary(roles)
    assert len(summary.clusters) == 1
    assert '0 confirmed / 2 conditional builds' in summary.lines[1]
    assert roles == saved
    assert summary.details[0]['rule_trace']['children'][0]['expected'] == 'Warlock'
    assert summary.details[1]['rule_trace']['children'][0]['expected'] == 'Paladin'
    # Actual wearer restrictions and distinct mercenary equipment remain distinct.
    assert len(build_use_summary([{**r, 'side': 'player'} for r in roles]).clusters) == 2
    different = deepcopy(roles)
    different[1]['rule_trace']['children'][1]['expected'] = 'other base'
    assert len(build_use_summary(different).clusters) == 2
    different = deepcopy(roles)
    different[1]['dependencies'] = [{'label': 'Prayer mercenary'}]
    assert len(build_use_summary(different).clusters) == 2
    different = deepcopy(roles)
    different[1]['rule_trace']['children'][0]['truth'] = 'false'
    assert len(build_use_summary(different).clusters) == 2


def test_each_visible_group_keeps_a_representative_build_label():
    roles = [role(i) for i in range(5)] + [role(10, side='player'), role(11, variant='Endgame')]
    summary = build_use_summary(roles)
    assert len(summary.clusters) == 3
    assert all(': Build ' in line for line in summary.lines[2:5])
    assert len(summary.lines) <= 8


def test_applicable_socket_preparation_is_visible_without_unrelated_requirements():
    roles = [
        role(1, socket_requirement={'item': 'Zod Rune', 'confirmed': False, 'applicable': True}),
        role(2, socket_requirement={'item': 'Zod Rune', 'confirmed': False, 'applicable': True}),
        role(3, socket_requirement={'item': 'Cham Rune', 'confirmed': True, 'applicable': True}),
        role(4, socket_requirement={'item': 'Ber Rune', 'confirmed': False, 'applicable': False}),
    ]
    text = '\n'.join(build_use_summary(roles).lines)
    assert text.count('Socket requirement: Zod (not confirmed)') == 1
    assert 'Cham' not in text
    assert 'Ber' not in text


def test_only_failed_candidates_without_demand_do_not_add_a_compact_build_section():
    from inventory_tracking.appraisal.build_use_summary import detail_lines

    failed = role(1, status='failed', failed=['Required charm modifiers are absent'])
    summary = build_use_summary([failed])
    assert summary.lines == ()
    assert len(summary.details) == len(summary.clusters) == 1
    assert 'Required charm modifiers are absent' in '\n'.join(detail_lines(summary))
    assert build_use_summary([role(2, status='unknown')]).lines
    assert build_use_summary([failed], {'grade': 'Low', 'distinct_builds': 1, 'complete': True}).lines


def test_compact_report_explains_visible_companion_requirements_without_failed_roles():
    roles = []
    for ident, state, dependency_state in [
        ('paired', 'partial', 'true'),
        ('missing', 'partial', 'false'),
        ('failed', 'failed', 'false'),
    ]:
        roles.append(
            {
                'id': ident,
                'build': 'echoing-strike-warlock-guide',
                'variant': 'Ubers',
                'side': 'player',
                'slot': 'Ring',
                'role': ident,
                'status': state,
                'dependencies': [
                    {
                        'label': ident + ' companion',
                        'status': dependency_state,
                        'trace': {'reason': 'player_items: companion'},
                    }
                ],
            }
        )
    text = '\n'.join(build_use_summary(roles).lines)
    assert 'Setup: paired companion' in text
    assert 'Needs: missing companion' in text
    assert 'Needs: failed companion' not in text


def test_unknown_companion_evidence_is_not_reported_as_present():
    role = {
        'id': 'sling',
        'build': 'echoing-strike-warlock-guide',
        'variant': 'Ubers',
        'side': 'player',
        'slot': 'Ring',
        'role': 'pairing',
        'status': 'partial',
        'dependencies': [{'label': 'Hellwarden', 'status': 'unknown', 'trace': {'reason': 'player_items: Hellwarden'}}],
    }
    text = '\n'.join(build_use_summary([role]).lines)
    assert 'Check: Hellwarden' in text
    assert 'Setup: Hellwarden' not in text


def test_satisfied_setup_is_visible_before_known_wrong_starter_mercenaries():
    wrong = [
        role(i, dependencies=[{'label': 'Wrong mercenary', 'status': 'false'}], role=f'Other setup {i}')
        for i in range(4)
    ]
    applicable = role(
        'z',
        variant='Standard',
        dependencies=[
            {
                'label': 'Cure in the mercenary setup',
                'status': 'true',
                'trace': {'reason': 'mercenary_items: Cure'},
            }
        ],
    )
    unknown = role('a', dependencies=[{'label': 'Mercenary unknown', 'status': 'unknown'}])
    summary = build_use_summary([*wrong, unknown, applicable])
    assert summary.clusters[0][0]['id'] == 'z'
    assert summary.clusters[1][0]['id'] == 'a'
    assert 'Setup: Cure in the mercenary setup' in '\n'.join(summary.lines)
    assert len(summary.details) == 6
    assert applicable['status'] == 'partial'


def test_base_preparation_is_actionable_without_repeating_satisfied_requirements():
    from inventory_tracking.appraisal.build_use_summary import companion_lines

    for state, expected in (
        ('false', ('    Needs: Upgrade to Mirrored Boots',)),
        ('unknown', ('    Check: Upgrade to Mirrored Boots',)),
        ('true', ()),
    ):
        candidate = role(
            'boots',
            side='player',
            dependencies=[
                {
                    'label': 'Upgrade to Mirrored Boots',
                    'status': state,
                    'trace': {'reason': 'base_code: utb', 'truth': state},
                }
            ],
        )
        assert companion_lines(candidate) == expected
        assert companion_lines({**candidate, 'status': 'failed'}) == ()


def test_nested_socket_preparation_reports_missing_and_uncertain_payload():
    from inventory_tracking.appraisal.build_use_summary import companion_lines

    for status, prefix in (('false', 'Needs'), ('unknown', 'Check')):
        candidate = role(
            'facet',
            dependencies=[
                {
                    'label': 'Socket a Fire Rainbow Facet',
                    'status': status,
                    'trace': {
                        'reason': 'all',
                        'children': [
                            {'reason': 'sockets: 1', 'truth': 'true'},
                            {'reason': '1 socket jewel(s) match all required stats', 'truth': status},
                        ],
                    },
                }
            ],
        )
        assert companion_lines(candidate) == (f'    {prefix}: Socket a Fire Rainbow Facet',)
        assert companion_lines({**candidate, 'status': 'failed'}) == ()
        candidate['dependencies'][0]['status'] = 'true'
        assert companion_lines(candidate) == ()


def test_visible_socket_plan_is_actionable_and_keeps_payloads_separate():
    facet = (
        'The sockets still need the four Rainbow Facets specified for this build; '
        'verify their properties before investing.'
    )
    ist = 'The sockets still need four Ist runes; verify their properties before investing.'
    roles = [
        role('a', missing=[facet], rule_trace={'truth': 'true'}),
        role('b', missing=[facet], rule_trace={'truth': 'true'}),
        role('c', variant='Magic Find', missing=[ist], rule_trace={'truth': 'true'}),
        role('d', status='failed', failed=['Required role properties are not satisfied.'], missing=[facet]),
    ]
    saved = deepcopy(roles)
    summary = build_use_summary(roles)
    text = '\n'.join(summary.lines)
    assert text.count('Needs: four Rainbow Facets') == 1
    assert text.count('Needs: four Ist runes') == 1
    assert 'Required role properties are not satisfied.' not in text
    assert 'verify their properties before investing' not in text
    assert roles == saved
    from inventory_tracking.appraisal.build_use_summary import detail_lines

    assert facet in '\n'.join(detail_lines(summary))
    assert 'Required role properties are not satisfied.' in '\n'.join(detail_lines(summary))


def test_unverified_or_failed_socket_plan_is_not_a_preparation_instruction():
    note = 'The sockets still need four Ist runes; verify their properties before investing.'
    for status, truth in (('failed', 'false'), ('partial', 'unknown'), ('unknown', 'true')):
        summary = build_use_summary([role(1, status=status, missing=[note], rule_trace={'truth': truth})])
        assert not any('Needs: four Ist' in line for line in summary.lines)


def test_negated_equipment_dependency_remains_visible_in_compact_report():
    from inventory_tracking.appraisal.build_use_summary import companion_lines

    for status, heading in (('true', 'Setup'), ('false', 'Needs'), ('unknown', 'Check')):
        label = 'This Teleport-charge alternative requires Enigma not to be equipped.'
        candidate = role(
            1,
            dependencies=[
                {
                    'label': label,
                    'status': status,
                    'trace': {
                        'reason': 'not',
                        'truth': status,
                        'children': [
                            {
                                'reason': 'player_items: Enigma',
                                'truth': 'unknown' if status == 'unknown' else 'false' if status == 'true' else 'true',
                            }
                        ],
                    },
                }
            ],
        )
        assert companion_lines(candidate) == (f'    {heading}: {label}',)
        assert companion_lines({**candidate, 'status': 'failed'}) == ()


def test_nested_alternative_uses_parent_truth_instead_of_one_satisfied_child():
    from inventory_tracking.appraisal.build_use_summary import companion_lines

    candidate = role(
        1,
        dependencies=[
            {
                'label': 'Spirit on swap and a supported mercenary weapon',
                'status': 'false',
                'trace': {
                    'reason': 'all',
                    'truth': 'false',
                    'children': [
                        {'reason': 'player_swap_items: Spirit', 'truth': 'true'},
                        {
                            'reason': 'any',
                            'truth': 'false',
                            'children': [
                                {'reason': 'mercenary_items: Infinity', 'truth': 'false'},
                                {'reason': 'mercenary_items: Insight', 'truth': 'false'},
                            ],
                        },
                    ],
                },
            }
        ],
    )
    assert companion_lines(candidate) == ('    Needs: Spirit on swap and a supported mercenary weapon',)
