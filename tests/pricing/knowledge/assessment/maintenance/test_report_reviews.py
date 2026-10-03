"""Only executed, source-bound, independently specified reports can close a gate."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.report_reviews import review_dimensions


def evidence():
    role = {'id': 'role', 'qualities': ['magic'], 'important_stats': ['7:0']}
    config = {'id': 'config', 'role_id': 'role', 'priorities': [{'key': '7:0'}]}
    profiles = {'profiles': [role], 'stat_evaluation': {'configurations': [config]}}
    inputs = {'tests/fixture.py': 'hash'}
    cases = {}
    for name, scenario, value, truth in (
        ('minimum', 'positive', 36, 'true'),
        ('maximum', 'positive', 45, 'true'),
        ('low', 'negative', 5, 'false'),
        ('unread', 'unknown', None, 'unknown'),
    ):
        text = f'+{value} to Life'
        line = {'text': '  ' + text, 'tone': 'perfect' if value == 45 else 'default'}
        checks = {
            'schema_version': 1,
            'role_id': 'role',
            'configuration_id': 'config',
            'truth': truth,
            'stats': []
            if value is None
            else [
                {
                    'keys': ['7:0'],
                    'data': {
                        'text': text,
                        'status': 'decoded',
                        'value': value,
                        'roll_quality': 'perfect' if value == 45 else 'normal',
                        'roll_tier': 1 if value == 45 else 2,
                        'roll_range': {'min': 5, 'max': 45},
                    },
                    'line': line,
                }
            ],
            'absent_stats': ['7:0'] if value is None else [],
            'osd': [
                {'text': 'Item: Magic Charm', 'tone': 'magic'},
                {'text': 'Observed stats:', 'tone': 'heading'},
                *([line] if value is not None else []),
                {'text': 'Price: unknown', 'tone': 'default'},
            ],
            'price': {'estimate_ist': None},
        }
        cases[name] = {
            'scenario': scenario,
            'covers': ['role'],
            'quality': 'magic',
            'complete': value is not None,
            'report_checks': checks,
            'phases': {'setup': 'passed', 'call': 'passed', 'teardown': 'passed'},
        }
    review = {
        'role_id': 'role',
        'quality': 'magic',
        'profile_fingerprint': fingerprint(role),
        'configuration_id': 'config',
        'configuration_fingerprint': fingerprint(config),
        'dimensions': ['report', 'stat_annotations'],
        'review_date': '2026-10-01',
        'reason': 'Reviewed native life range, displayed tier, color, identity and price outcome.',
        'receipt': 'pricing/data/report-receipts/example.json',
        'cases': {name: fingerprint(c['report_checks']) for name, c in cases.items()},
        'stats': {'7:0': {'kind': 'variable', 'min': 5, 'max': 45}},
    }
    receipt = {
        'schema_version': 1,
        'generation': 'selected',
        'exitstatus': 0,
        'sources_unchanged': True,
        'inputs': inputs,
        'finished_inputs': inputs,
        'cases': cases,
        'passed_cases': list(cases),
        'full_bank_passed': False,
    }
    return {'schema_version': 1, 'rows': [review]}, profiles, {review['receipt']: receipt}, 'selected', inputs


def test_exact_use_review_closes_only_the_two_declared_dimensions():
    rows, receipts = review_dimensions(*evidence())
    assert set(rows) == {'use:role:magic'}
    assert set(rows['use:role:magic']) == {'report', 'stat_annotations'}
    assert {d['state'] for d in rows['use:role:magic'].values()} == {'reviewed'}
    assert receipts == {'pricing/data/report-receipts/example.json'}


@pytest.mark.parametrize('failure', ['missing', 'generation', 'sources', 'exit', 'case', 'phase', 'expectations'])
def test_incomplete_or_stale_execution_never_closes_a_review(failure):
    args = list(evidence())
    receipt = next(iter(args[2].values()))
    if failure == 'missing':
        args[2] = {}
    elif failure == 'generation':
        receipt['generation'] = 'older'
    elif failure == 'sources':
        receipt['inputs'] = {'tests/fixture.py': 'older'}
    elif failure == 'exit':
        receipt['exitstatus'] = 1
    elif failure == 'case':
        receipt['cases'].pop('unread')
    elif failure == 'phase':
        receipt['cases']['maximum']['phases']['teardown'] = 'failed'
    else:
        receipt['cases']['maximum']['report_checks']['stats'][0]['data']['value'] = 50
    rows, receipts = review_dimensions(*args)
    assert {d['state'] for d in rows['use:role:magic'].values()} == {'pending'}
    assert receipts == set()


@pytest.mark.parametrize('failure', ['profile', 'config', 'quality', 'keys', 'dimensions', 'duplicate'])
def test_wrong_scope_or_source_review_is_rejected(failure):
    args = list(evidence())
    review = args[0]['rows'][0]
    if failure == 'profile':
        review['profile_fingerprint'] = 'stale'
    elif failure == 'config':
        review['configuration_fingerprint'] = 'stale'
    elif failure == 'quality':
        review['quality'] = 'rare'
    elif failure == 'keys':
        review['stats']['9:0'] = {'kind': 'fixed'}
    elif failure == 'dimensions':
        review['dimensions'].append('market')
    else:
        args[0]['rows'].append(deepcopy(review))
    with pytest.raises(ValueError, match=r'report.review|Report.review|Duplicate'):
        review_dimensions(*args)


@pytest.mark.parametrize('omission', ['unknown', 'minimum_bound', 'full_report', 'range', 'native_key'])
def test_passing_cases_without_required_assertions_are_not_sufficient(omission):
    args = list(evidence())
    review = args[0]['rows'][0]
    receipt = next(iter(args[2].values()))
    if omission == 'unknown':
        review['cases'].pop('unread')
    elif omission == 'minimum_bound':
        review['cases'].pop('low')
    else:
        for case in receipt['cases'].values():
            checks = case['report_checks']
            if omission == 'full_report':
                checks.pop('osd')
            elif omission == 'range':
                for stat in checks['stats']:
                    stat['data']['roll_range'] = None
            elif omission == 'native_key':
                for stat in checks['stats']:
                    stat['keys'] = ['9:0']
        review['cases'] = {name: fingerprint(case['report_checks']) for name, case in receipt['cases'].items()}
    rows, receipts = review_dimensions(*args)
    assert {d['state'] for d in rows['use:role:magic'].values()} == {'pending'}
    assert not receipts


def test_stat_only_review_does_not_certify_full_report():
    args = list(evidence())
    args[0]['rows'][0]['dimensions'] = ['stat_annotations']
    for case in next(iter(args[2].values()))['cases'].values():
        case['report_checks'].pop('osd')
    args[0]['rows'][0]['cases'] = {
        name: fingerprint(case['report_checks']) for name, case in next(iter(args[2].values()))['cases'].items()
    }
    rows, accepted = review_dimensions(*args)
    assert set(rows['use:role:magic']) == {'stat_annotations'}
    assert rows['use:role:magic']['stat_annotations']['state'] == 'reviewed'
    assert accepted


def test_matrix_application_keeps_other_rows_and_dimensions_pending():
    from pricing.knowledge.assessment.maintenance.report_reviews import apply_report_reviews

    rows = [
        {'id': row_id, 'dimensions': {d: {'state': 'pending'} for d in ('report', 'stat_annotations', 'market')}}
        for row_id in ('use:role:magic', 'use:role:rare', 'identity:charm')
    ]
    assert apply_report_reviews(rows, *evidence()) == {'pricing/data/report-receipts/example.json'}
    assert rows[0]['dimensions']['report']['state'] == 'reviewed'
    assert rows[0]['dimensions']['market']['state'] == 'pending'
    assert all(d['state'] == 'pending' for row in rows[1:] for d in row['dimensions'].values())
    with pytest.raises(ValueError, match='missing'):
        apply_report_reviews([], *evidence())


def test_staged_profiles_cannot_borrow_selected_generation_receipts(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace

    from pricing.knowledge import publication
    from pricing.knowledge.assessment.maintenance import verification_scope
    from pricing.knowledge.assessment.maintenance.report_reviews import load_review_context

    document, profiles, receipts, _, inputs = evidence()
    published = tmp_path / 'published-profiles.json'
    published.write_text(json.dumps(profiles))
    monkeypatch.setattr(
        publication,
        'current_generation',
        lambda _: SimpleNamespace(
            generation='selected',
            artifact=lambda _: published,
        ),
    )
    monkeypatch.setattr(verification_scope, 'verification_inputs', lambda _: inputs)
    path = tmp_path / document['rows'][0]['receipt']
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(next(iter(receipts.values()))))
    assert load_review_context(tmp_path, document, profiles) == (receipts, 'selected', inputs)
    profiles['profiles'][0]['new_requirement'] = True
    assert load_review_context(tmp_path, document, profiles) == (receipts, None, inputs)
    document['rows'][0]['receipt'] = '../outside.json'
    with pytest.raises(ValueError, match='escapes'):
        load_review_context(tmp_path, document, profiles)


def test_completion_rechecks_receipt_generation_and_reviewed_dimensions():
    from pricing.knowledge.assessment.maintenance.report_reviews import validate_published_reviews

    document, profiles, receipts, generation, inputs = evidence()
    dimensions, _ = review_dimensions(document, profiles, receipts, generation, inputs)
    matrix = {
        'rows': [{'id': key, 'dimensions': value} for key, value in dimensions.items()],
        'report_receipts': list(receipts),
    }
    sources = {
        'report_reviews': document,
        'profiles': profiles,
        **{'receipt:' + key: value for key, value in receipts.items()},
    }
    validate_published_reviews(matrix, sources, generation, inputs)
    with pytest.raises(ValueError, match='report'):
        validate_published_reviews(matrix, sources, 'different', inputs)
    changed = deepcopy(matrix)
    changed['rows'][0]['dimensions']['report']['reason'] = 'unreviewed replacement'
    with pytest.raises(ValueError, match='report'):
        validate_published_reviews(changed, sources, generation, inputs)


def test_partial_stat_presentation_assertions_can_prove_annotations_but_not_full_report():
    args = list(evidence())
    review = args[0]['rows'][0]
    review['dimensions'] = ['stat_annotations']
    cases = next(iter(args[2].values()))['cases']
    for case in cases.values():
        checks = case['report_checks']
        checks.pop('osd')
        for stat in checks['stats']:
            stat.pop('line')
            stat['body'] = {
                'text': stat['data']['text'],
                'tone': 'perfect' if stat['data']['roll_quality'] == 'perfect' else 'default',
            }
            stat['priority'] = 'supporting'
    review['cases'] = {name: fingerprint(case['report_checks']) for name, case in cases.items()}
    rows, accepted = review_dimensions(*args)
    assert rows['use:role:magic']['stat_annotations']['state'] == 'reviewed'
    assert 'report' not in rows['use:role:magic']
    assert accepted
    review['dimensions'].append('report')
    rows, accepted = review_dimensions(*args)
    assert rows['use:role:magic']['report']['state'] == 'pending'
    assert not accepted


def test_review_rejects_a_color_expectation_that_contradicts_the_roll_quality():
    args = list(evidence())
    review = args[0]['rows'][0]
    receipt = next(iter(args[2].values()))
    case = receipt['cases']['maximum']
    case['report_checks']['stats'][0]['line']['tone'] = 'default'
    review['cases']['maximum'] = fingerprint(case['report_checks'])
    rows, accepted = review_dimensions(*args)
    assert rows['use:role:magic']['stat_annotations']['state'] == 'pending'
    assert not accepted
