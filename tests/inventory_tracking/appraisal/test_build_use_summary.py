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
