"""Offline selection analysis and equal-or-worse asking-price comparisons."""

from math import isfinite, log2
from statistics import median, quantiles


def numeric(value):
    return type(value) in (int, float) and isfinite(value)


def seller_rows(rows):
    votes = {}
    for row in rows:
        price = row.get('ask_ist')
        seller = row.get('seller_id')
        if seller is not None and numeric(price) and price > 0:
            key = str(seller)
            if key not in votes or price < votes[key]['ask_ist']:
                votes[key] = row
    return list(votes.values())


def position(value, spec):
    result = (value - spec['min']) / (spec['max'] - spec['min'])
    return 1 - result if spec.get('better') == 'lower' else result


def deciding_stats(rows, ranges, *, minimum_sellers=15, top_fraction=0.75):
    """A draft deciding stat needs independent sellers concentrated in its best quartile."""
    selected = {}
    for prop, spec in ranges.items():
        if spec['min'] >= spec['max']:
            continue
        valid = [
            r
            for r in rows
            if numeric(r.get('properties', {}).get(prop)) and spec['min'] <= r['properties'][prop] <= spec['max']
        ]
        values = [r['properties'][prop] for r in seller_rows(valid)]
        top = sum(position(value, spec) >= 0.75 for value in values)
        if len(values) >= minimum_sellers and top / len(values) >= top_fraction:
            selected[prop] = {
                **spec,
                'sample_size': len(values),
                'top_count': top,
                'observed_min': min(values),
                'observed_max': max(values),
            }
    return selected


def price_split(rows, prop, spec, *, minimum_sellers=6, side=3, ratio=1.5):
    """A roll that most sellers do not maximise still decides price when asks split on it.

    Both the lower quartile and the median of the better side must be `ratio` times the
    worse side's, with `side` independent sellers on each: one cheap or one dear ask
    cannot create the split.
    """
    votes = [
        r
        for r in seller_rows(rows)
        if numeric(r.get('properties', {}).get(prop)) and spec['min'] <= r['properties'][prop] <= spec['max']
    ]
    if len(votes) < minimum_sellers:
        return None
    values = [r['properties'][prop] for r in votes]
    for boundary in sorted(set(values))[1:]:
        low = [r['ask_ist'] for r in votes if r['properties'][prop] < boundary]
        high = [r['ask_ist'] for r in votes if r['properties'][prop] >= boundary]
        good, bad = (low, high) if spec.get('better') == 'lower' else (high, low)
        if (
            min(len(low), len(high)) >= side
            and lower_quartile(good) >= ratio * lower_quartile(bad)
            and median(good) >= ratio * median(bad)
        ):
            return {
                **spec,
                'sample_size': len(values),
                'top_count': sum(position(value, spec) >= 0.75 for value in values),
                'observed_min': min(values),
                'observed_max': max(values),
                'price_split': boundary,
            }
    return None


def split_validated(validation, *, minimum_sellers=6, margin=0.9):
    """Held-out sellers priced clearly better with the rolls than with the name median."""
    roll, name = validation['roll_median_error'], validation['name_median_error']
    return validation['evaluated'] >= minimum_sellers and roll <= margin * name


def price_split_stats(rows, ranges, deciding):
    """Price-split rolls that lower the held-out asking-price error, added one at a time.

    The split test alone passes on noise (several rolls, several boundaries each), so a
    candidate is kept only when predicting each held-out seller with it beats the name
    median by a margin and the rolls already accepted; the whole set must then pass again
    with the splits re-tested inside every fold.
    """
    accepted = {}
    error = leave_one_out(rows, deciding)['roll_median_error'] if deciding else None
    for prop, spec in ranges.items():
        if prop in deciding or spec['min'] >= spec['max']:
            continue
        candidate = price_split(rows, prop, spec)
        if candidate is None:
            continue
        trial = leave_one_out(rows, deciding | accepted | {prop: candidate})
        if split_validated(trial) and (error is None or trial['roll_median_error'] < error):
            accepted[prop], error = candidate, trial['roll_median_error']
    if accepted and not split_validated(leave_one_out(rows, deciding | accepted, ranges=ranges, minimum_sellers=1)):
        return {}
    return accepted


def comparable(row, properties, deciding):
    for prop, spec in deciding.items():
        value = row.get('properties', {}).get(prop)
        if not numeric(value) or not spec['min'] <= value <= spec['max']:
            return False
        if spec.get('better') == 'lower':
            if value < properties[prop]:
                return False
        elif value > properties[prop]:
            return False
    return True


def lower_quartile(values):
    return quantiles(values, n=4, method='inclusive')[0] if len(values) > 1 else values[0] if values else None


def compare(properties, rows, deciding, *, keep_ist):
    missing = [spec.get('label', prop) for prop, spec in deciding.items() if not numeric(properties.get(prop))]
    result = {'verdict': 'check', 'q1_ist': None, 'sellers': 0, 'upper_bound_ist': None}
    if missing:
        return {**result, 'reason': 'unreadable deciding roll: ' + ', '.join(missing)}
    invalid = [
        spec.get('label', prop) for prop, spec in deciding.items() if not spec['min'] <= properties[prop] <= spec['max']
    ]
    if invalid:
        return {**result, 'reason': 'deciding roll outside native range: ' + ', '.join(invalid)}
    selected = seller_rows([r for r in rows if comparable(r, properties, deciding)])
    values = [r['ask_ist'] for r in selected]
    price = lower_quartile(values)
    label = ', '.join(f'{spec.get("label", prop)} {properties[prop]:g}' for prop, spec in deciding.items())
    result.update(q1_ist=price, sellers=len(selected))
    if price is not None:
        # Within the listed range, sparse evidence cannot establish either price disposition.
        result['verdict'] = 'check' if len(selected) < 3 else 'vendor' if price < keep_ist else 'priced'
        result['reason'] = f'asks {price:g} Ist lower quartile; {len(selected)} comparable-or-worse sellers ({label})'
    else:
        known = seller_rows(
            [
                r
                for r in rows
                if all(
                    numeric(r.get('properties', {}).get(p)) and spec['min'] <= r['properties'][p] <= spec['max']
                    for p, spec in deciding.items()
                )
            ]
        )
        below = [
            spec.get('label', prop)
            for prop, spec in deciding.items()
            if known
            and all(
                (
                    r['properties'][prop] < properties[prop]
                    if spec.get('better') == 'lower'
                    else r['properties'][prop] > properties[prop]
                )
                for r in known
            )
        ]
        if below:
            ceiling = min(r['ask_ist'] for r in known)
            result.update(
                upper_bound_ist=ceiling,
                verdict='vendor' if ceiling < keep_ist else 'check',
                reason=f'below listed rolls ({label}); cheapest listed ask {ceiling:g} Ist is an upper bound',
            )
        else:
            result['reason'] = f'no comparable-or-worse sellers for the full combination ({label})'
    return result


def leave_one_out(rows, deciding, *, ranges=None, minimum_sellers=15):
    """Compare both predictors on the same held-out sellers using absolute log2 price error."""
    roll_errors, name_errors = [], []
    for held in seller_rows(rows):
        training = [r for r in rows if str(r.get('seller_id')) != str(held['seller_id'])]
        selected = deciding_stats(training, ranges, minimum_sellers=minimum_sellers) if ranges is not None else deciding
        # Guide-declared axes are independent of the held-out listing. Keep
        # them when recomputing market-selected axes on the training sellers.
        selected = selected | {prop: spec for prop, spec in deciding.items() if spec.get('guide_source')}
        if ranges is not None:
            # A price split is re-tested without the held-out seller, like the selection signal.
            selected = selected | {
                prop: spec
                for prop, spec in deciding.items()
                if 'price_split' in spec and prop not in selected and price_split(training, prop, ranges[prop])
            }
        if not selected:
            continue
        result = compare(held.get('properties', {}), training, selected, keep_ist=0)
        estimate = result['q1_ist']
        votes = seller_rows(training)
        if estimate is None or not votes:
            continue
        baseline = median(r['ask_ist'] for r in votes)
        roll_errors.append(abs(log2(estimate / held['ask_ist'])))
        name_errors.append(abs(log2(baseline / held['ask_ist'])))
    roll = median(roll_errors) if roll_errors else None
    name = median(name_errors) if name_errors else None
    return {
        'evaluated': len(roll_errors),
        'seller_exclusion': True,
        'selection_recomputed': ranges is not None,
        'roll_median_error': roll,
        'name_median_error': name,
        'error_unit': 'absolute log2 price ratio',
        'use_roll_model': roll is not None and roll < name,
        'paired_errors': list(zip(roll_errors, name_errors, strict=True)),
    }


def fallback_required(validation):
    roll, name = validation.get('roll_median_error'), validation.get('name_median_error')
    return roll is not None and name is not None and roll > name


def validation_summary(reports):
    pairs = [pair for report in reports for pair in report['validation'].get('paired_errors', [])]
    deployed = [
        pair[1] if fallback_required(report['validation']) else pair[0]
        for report in reports
        for pair in report['validation'].get('paired_errors', [])
    ]
    return {
        'evaluated': len(pairs),
        'roll_median_error': median(p[0] for p in pairs) if pairs else None,
        'name_median_error': median(p[1] for p in pairs) if pairs else None,
        'deployed_median_error': median(deployed) if deployed else None,
        'error_unit': 'absolute log2 price ratio',
        'fallbacks': [
            {k: report.get(k) for k in ('name', 'ethereal', 'socket_contents', 'coarse_facets')}
            for report in reports
            if fallback_required(report['validation'])
        ],
    }
