"""Exact-use report coverage backed by executed, source-pinned item-bank cases.

A receipt closes only declared dimensions for one role and quality. It cannot
establish identity-wide coverage or stand in for a final full-bank run.
"""

from datetime import date
from pathlib import PurePosixPath

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint


DIMENSIONS = frozenset({'report', 'stat_annotations'})
TRUTHS = {'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}
STAT_FIELDS = frozenset({'text', 'status', 'roll_range', 'roll_tier', 'roll_quality'})


def _validate_review(review, roles, configurations):
    role = roles.get(review['role_id'])
    config = configurations.get(review['configuration_id'])
    if role is None or review.get('profile_fingerprint') != fingerprint(role):
        raise ValueError('Missing or stale report-review role')
    if (
        config is None
        or config.get('role_id') != role['id']
        or review.get('configuration_fingerprint') != fingerprint(config)
    ):
        raise ValueError('Missing or stale report-review configuration')
    if review['quality'] not in role['qualities']:
        raise ValueError('Report-review quality outside role scope')
    dimensions = review.get('dimensions', [])
    if not dimensions or not set(dimensions) <= DIMENSIONS or len(set(dimensions)) != len(dimensions):
        raise ValueError('Invalid report-review dimensions')
    keys = set(role.get('important_stats', [])) | {p['key'] for p in config['priorities']}
    if set(review.get('stats', {})) != keys:
        raise ValueError('Report-review native keys differ from role/configuration')
    for specification in review['stats'].values():
        if specification.get('kind') not in {'fixed', 'variable'}:
            raise ValueError('Unknown report-review stat kind')
        if specification['kind'] == 'variable':
            bounds = [specification.get('min'), specification.get('max')]
            if any(type(n) not in (int, float) for n in bounds) or bounds[0] >= bounds[1]:
                raise ValueError('Invalid report-review variable bounds')
    path = PurePosixPath(review['receipt'])
    if path.is_absolute() or '..' in path.parts or not path.is_relative_to('pricing/data/report-receipts'):
        raise ValueError('Receipt must be inside pricing/data/report-receipts')
    date.fromisoformat(review['review_date'])
    if not isinstance(review.get('reason'), str) or not review['reason'].strip():
        raise ValueError('Report review requires a rationale')
    if not isinstance(review.get('cases'), dict) or not review['cases']:
        raise ValueError('Report review requires independently specified cases')


def _execution_cases(review, receipt, generation, inputs):
    if not receipt or receipt.get('schema_version') != 1:
        return None, 'Missing execution receipt.'
    if not generation or receipt.get('generation') != generation:
        return None, 'Receipt does not verify the selected generation.'
    if (
        receipt.get('exitstatus') != 0
        or receipt.get('sources_unchanged') is not True
        or receipt.get('inputs') != inputs
        or receipt.get('finished_inputs') != inputs
    ):
        return None, 'Execution failed or verification sources changed.'
    cases = []
    for name, expected_hash in review['cases'].items():
        case = receipt.get('cases', {}).get(name)
        if not case or any(case.get('phases', {}).get(p) != 'passed' for p in ('setup', 'call', 'teardown')):
            return None, 'A required case did not pass every test phase.'
        checks = case.get('report_checks', {})
        if fingerprint(checks) != expected_hash:
            return None, 'Executed assertions differ from the reviewed case contract.'
        if (
            case.get('quality') != review['quality']
            or review['role_id'] not in case.get('covers', [])
            or checks.get('schema_version') != 1
            or checks.get('role_id') != review['role_id']
            or checks.get('configuration_id') != review['configuration_id']
            or case.get('scenario') not in TRUTHS
            or checks.get('truth') != TRUTHS[case['scenario']]
        ):
            return None, 'Case assertions do not address the reviewed use and scenario.'
        cases.append(case)
    if {c['scenario'] for c in cases} != set(TRUTHS):
        return None, 'Positive, negative and unknown cases are all required.'
    return cases, None


def _has_stat_presentation(stat, *, positive):
    quality = stat.get('data', {}).get('roll_quality')
    if quality not in {None, 'normal', 'perfect', 'low'}:
        return False
    tone = quality if quality in {'perfect', 'low'} else 'default'
    line = stat.get('line')
    if isinstance(line, dict) and 'text' in line and 'tone' in line:
        spans = line.get('spans')
        return (
            spans[-1].get('tone') if isinstance(spans, list) and spans and isinstance(spans[-1], dict) else line['tone']
        ) == tone
    body = stat.get('body')
    return (
        isinstance(body, dict)
        and set(body) == {'text', 'tone'}
        and bool(body['text'])
        and body['text'] == stat.get('data', {}).get('text')
        and body['tone'] == tone
        and (not positive or stat.get('priority') in {'desirable', 'supporting'})
    )


def _assertion_gap(review, cases):
    positive_keys = set()
    boundary_values = {key: set() for key in review['stats']}
    for case in cases:
        checks = case['report_checks']
        if 'report' in review['dimensions']:
            lines = checks.get('osd')
            price = checks.get('price')
            if not isinstance(lines, list) or not lines or not isinstance(price, dict) or 'estimate_ist' not in price:
                return 'Full OSD and explicit price expectations are required.'
            texts = [line.get('text', '').strip() for line in lines]
            if not any(t.startswith('Item:') for t in texts) or 'Observed stats:' not in texts:
                return 'Report expectations omit item identity or observed stats.'
            if not any(t.startswith(('Price:', 'Comparable asks')) for t in texts):
                return 'Report expectations omit the pricing disposition.'
        for stat in checks.get('stats', []):
            keys = stat.get('keys', [])
            data = stat.get('data', {})
            if (
                not keys
                or len(keys) != len(set(keys))
                or not set(keys) <= set(review['stats'])
                or not set(data) >= STAT_FIELDS
                or data.get('status') != 'decoded'
                or not _has_stat_presentation(stat, positive=case['scenario'] == 'positive')
            ):
                return 'Native-stat, annotation and rendered-line expectations are incomplete.'
            if case['scenario'] == 'positive':
                positive_keys.update(keys)
            for key in keys:
                specification = review['stats'][key]
                if specification['kind'] != 'variable':
                    continue
                bounds = data.get('roll_range')
                if not isinstance(bounds, dict):
                    return 'A variable stat lacks a range assertion.'
                bounds = bounds.get('quality_range', bounds)
                if not isinstance(bounds, dict) or any(bounds.get(k) != specification[k] for k in ('min', 'max')):
                    return 'Variable range assertions do not match reviewed bounds.'
                if type(data.get('value')) not in (int, float):
                    return 'Variable boundary assertions require a scalar value.'
                boundary_values[key].add(data['value'])
    if positive_keys != set(review['stats']):
        return 'Positive cases do not assert every reviewed native stat.'
    for key, specification in review['stats'].items():
        if (
            specification['kind'] == 'variable'
            and not {specification['min'], specification['max']} <= boundary_values[key]
        ):
            return 'Variable minimum and maximum boundaries have not both been exercised.'
    return None


def review_dimensions(document, profiles, receipts, generation, inputs):
    """Return exact-use dimension evidence and only receipts actually accepted."""
    if document.get('schema_version') != 1:
        raise ValueError('Unsupported report-review schema')
    roles = {r['id']: r for r in profiles['profiles']}
    configs = {c['id']: c for c in profiles.get('stat_evaluation', {}).get('configurations', [])}
    rows, accepted = {}, set()
    for index, review in enumerate(document['rows']):
        _validate_review(review, roles, configs)
        row_id = f'use:{review["role_id"]}:{review["quality"]}'
        if row_id in rows:
            raise ValueError('Duplicate report-review use/quality')
        cases, gap = _execution_cases(review, receipts.get(review['receipt']), generation, inputs)
        if gap is None:
            gap = _assertion_gap(review, cases)
        source = {'artifact': 'report_reviews', 'locator': f'/rows/{index}'}
        if gap is None:
            accepted.add(review['receipt'])
            source['receipt'] = review['receipt']
        rows[row_id] = {
            dimension: {
                'state': 'pending' if gap else 'reviewed',
                'reason': gap or review['reason'],
                'sources': [source],
            }
            for dimension in review['dimensions']
        }
    return rows, accepted


def apply_report_reviews(rows, document, profiles, receipts, generation, inputs):
    dimensions, accepted = review_dimensions(document, profiles, receipts, generation, inputs)
    by_id = {row['id']: row for row in rows}
    if dimensions.keys() - by_id.keys():
        raise ValueError('Report review addresses a missing coverage row')
    for row_id, reviewed in dimensions.items():
        by_id[row_id]['dimensions'].update(reviewed)
    return accepted


def load_review_context(root, document, profiles):
    """Load immutable published identity plus mutable execution evidence safely.

    A staged profile cannot borrow an older generation's successful receipt.
    Missing receipts are normal while work is pending; malformed files reject.
    """
    import json

    from pricing.knowledge.assessment.maintenance.verification_scope import verification_inputs
    from pricing.knowledge.publication import current_generation

    generation = current_generation(root / 'pricing/data/generations')
    published_profiles = json.loads(generation.artifact('pricing/data/appraisal-build-profiles.json').read_bytes())
    selected = generation.generation if fingerprint(published_profiles) == fingerprint(profiles) else None
    receipts = {}
    for row in document['rows']:
        path = (root / row['receipt']).resolve()
        receipt_root = (root / 'pricing/data/report-receipts').resolve()
        if not path.is_relative_to(receipt_root):
            raise ValueError('Receipt path escapes report receipt directory')
        if path.is_file():
            receipts[row['receipt']] = json.loads(path.read_bytes())
    return receipts, selected, verification_inputs(root)


def validate_published_reviews(matrix, source_documents, generation, inputs):
    """Completion must not reuse reviewed dimensions from an older generation."""
    document = source_documents.get('report_reviews')
    if document is None:
        if matrix.get('report_receipts'):
            raise ValueError('Missing report-review source')
        return
    receipts = {path: source_documents.get('receipt:' + path) for path in matrix.get('report_receipts', [])}
    dimensions, accepted = review_dimensions(document, source_documents['profiles'], receipts, generation, inputs)
    if accepted != set(matrix.get('report_receipts', [])):
        raise ValueError('Stale report execution evidence; rebuild the coverage matrix')
    rows = {row['id']: row['dimensions'] for row in matrix['rows']}
    for row_id, reviewed in dimensions.items():
        for key, value in reviewed.items():
            actual = rows.get(row_id, {}).get(key)
            if (value['state'] == 'reviewed' or (actual or {}).get('state') == 'reviewed') and actual != value:
                raise ValueError('Changed report dimension; rebuild the coverage matrix')
