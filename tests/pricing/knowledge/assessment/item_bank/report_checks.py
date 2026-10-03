"""Assert authored native-stat and presentation contracts against real appraisal."""

from dirty_equals import IsPartialDict

from inventory_tracking.appraisal.intrinsic_rolls import display_stats
from inventory_tracking.appraisal.presentation import ItemAssessment
from inventory_tracking.appraisal.stat_markers import stat_line


def native_keys(stat):
    native = ([stat['memory_stat']] if stat.get('memory_stat') else []) + list(stat.get('memory_stats', []))
    return {f'{entry["id"]}:{entry["layer"]}' for entry in native}


def partial(expected):
    if isinstance(expected, dict):
        return IsPartialDict({key: partial(value) for key, value in expected.items()})
    if isinstance(expected, list):
        return [partial(value) for value in expected]
    return expected


def assert_report_checks(result, checks):
    assert checks['schema_version'] == 1
    assessment = result['assessment']
    roles = [role for role in assessment['roles'] if role['id'] == checks['role_id']]
    assert len(roles) == 1
    assert roles[0]['rule_trace']['truth'] == checks['truth']
    annotations = assessment.get('stat_evaluation', {}).get('annotations', {})
    config = checks['configuration_id']
    if checks['truth'] != 'true':
        assert all(config not in annotation.get('configuration_ids', []) for annotation in annotations.values())
    stats = display_stats(result)
    osd = [
        line.to_payload()
        for line in ItemAssessment.from_record(
            {'state': 'complete', 'request_id': 'bank-report-check', 'result': result}
        ).to_osd()
    ]
    for expected in checks['stats']:
        keys = set(expected['keys'])
        found = [stat for stat in stats if native_keys(stat) == keys]
        assert len(found) == 1, (keys, found)
        # Missing optional annotation fields must be explicitly expected as None.
        actual = {**dict.fromkeys(('roll_range', 'roll_tier', 'roll_quality')), **found[0]}
        assert actual == partial(expected['data'])
        if 'line' in expected:
            assert stat_line(found[0], annotations).to_payload() == expected['line']
            assert osd.count(expected['line']) == 1
        else:
            assert_stat_body(osd, expected, active=checks['truth'] == 'true')
        if checks['truth'] == 'true':
            for key in keys:
                assert config in annotations.get(key, {}).get('configuration_ids', [])
                if 'priority' in expected:
                    contributions = [c for c in annotations[key]['contributions'] if c['configuration_id'] == config]
                    assert len(contributions) == 1
                    assert contributions[0]['desirability'] == expected['priority']
    for key in checks.get('absent_stats', []):
        assert not any(key in native_keys(stat) and stat.get('status') == 'decoded' for stat in stats)
    if 'osd' in checks:
        assert osd == checks['osd']
    if 'price' in checks:
        assert result['price_estimate'] == partial(checks['price'])


def assert_stat_body(osd, expected, *, active):
    """Verify the rendered property independently of stronger, unrelated uses."""
    body = expected['body']
    assert body['text'] == expected['data']['text']
    matches = [line for line in osd if line['text'].endswith(body['text'])]
    assert len(matches) == 1
    line = matches[0]
    assert line['tone'] == body['tone']
    spans = line.get('spans', [])
    if not spans:
        assert not active
        assert line['text'] == '  ' + body['text']
        return
    assert len(spans) == 2
    assert spans[-1] == body
    allowed = ['desirable'] if active and expected['priority'] == 'desirable' else ['desirable', 'supporting']
    assert spans[0] in [{'text': f'  ● [{kind}] ', 'tone': 'stat_' + kind} for kind in allowed]
    assert line['text'] == ''.join(span['text'] for span in spans)
