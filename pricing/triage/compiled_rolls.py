"""Compile roll comparisons offline; runtime only selects a precomputed cell."""

import json
from bisect import bisect_right
from itertools import product

from pricing.triage.adapters import expanded_properties
from pricing.triage.bands import band_for, eligible
from pricing.triage.roll_cohorts import matches_cohort
from pricing.triage.roll_comparisons import comparable, compare, fallback_required, lower_quartile, numeric, seller_rows


def key(values):
    return json.dumps(values, separators=(',', ':'))


def compile_model(report, rows, *, require_supported_split=False):
    reference_only = fallback_required(report['validation'])
    if not report['deciding'] or (reference_only and not require_supported_split):
        return None
    cohort = [
        r | {'properties': expanded_properties(r.get('properties', {}))}
        for r in rows
        if eligible(r)
        and r['name'].casefold() == report['name'].casefold()
        and r['category'] == report.get('category', r['category'])
        and matches_cohort(r, report)
        and r['amount'] == 1
    ]
    if not cohort:
        return None
    deciding = report['deciding']
    guided = {prop: spec for prop, spec in deciding.items() if 'guide_floor' in spec}
    selected = {
        prop: spec
        for prop, spec in deciding.items()
        if spec.get('sample_size', 0) >= 15 and spec.get('top_count', 0) / spec['sample_size'] >= 0.75
    }
    # Unlike a discovered selection signal, a declared guide floor has no
    # statistical calibration of its own. Missing validation is not approval.
    if guided and not report['validation'].get('use_roll_model'):
        reference_only = True
    if reference_only:
        # Rejected predictions must not publish prices. A robust selection
        # signal still caps below-selected rolls at CHECK (Steering 4).
        deciding = guided | selected
    elif require_supported_split:
        from pricing.triage.cohort_splits import roll_split

        supported = {prop: spec for prop, spec in deciding.items() if roll_split(cohort, prop)}
        safeguards = guided | selected
        if safeguards.keys() - supported.keys():
            # A guide establishes relevant rolls, not a supported numerical split.
            # Never silently omit one axis of its combination to publish a price.
            deciding, reference_only = safeguards, True
        else:
            deciding = supported
    if not deciding:
        return None
    deciding = {prop: dict(spec) for prop, spec in deciding.items()}
    for prop, spec in deciding.items():
        sign = -1 if spec.get('better') == 'lower' else 1
        valid = [
            r
            for r in cohort
            if numeric(r['properties'].get(prop)) and spec['min'] <= r['properties'][prop] <= spec['max']
        ]
        if valid:
            spec['selection_floor'] = sign * lower_quartile([sign * r['properties'][prop] for r in seller_rows(valid)])
    axes, stand_ins = {}, {}
    for prop, spec in deciding.items():
        sign = -1 if spec.get('better') == 'lower' else 1
        boundary = spec['max'] if sign == -1 else spec['min']
        observed = sorted(
            {
                sign * r['properties'][prop]
                for r in cohort
                if numeric(r['properties'].get(prop)) and spec['min'] <= r['properties'][prop] <= spec['max']
            }
        )
        if 'price_split' in spec:
            # The evidence supports one boundary, so the axis has two cells: every roll on
            # a side is priced with that side's sellers, not with the few at its exact value.
            split = spec['price_split']
            good = min(o for o in observed if (o > -split if sign == -1 else o >= split))
            axes[prop] = sorted({sign * boundary, good})
            stand_ins[prop] = {
                point: max((o for o in observed if point >= good or o < good), default=point) for point in axes[prop]
            }
            continue
        axes[prop] = sorted({sign * boundary, *observed})
    cells = {}
    for values in product(*axes.values()):
        properties = {
            p: stand_ins.get(p, {}).get(value, value) * (-1 if deciding[p].get('better') == 'lower' else 1)
            for p, value in zip(axes, values, strict=True)
        }
        result = compare(properties, cohort, deciding, keep_ist=0)
        selected = [r for r in cohort if comparable(r, properties, deciding)]
        band = band_for(cohort[0]['category'], report['name'], selected) if result['q1_ist'] is not None else None
        cells[key(values)] = {'band': band, 'upper_bound_ist': result['upper_bound_ist']}
    return {
        **report,
        'deciding': deciding,
        'reference_only': reference_only,
        'category': cohort[0]['category'],
        'axes': axes,
        'cells': cells,
        'reference_band': band_for(cohort[0]['category'], report['name'], cohort),
    }


def lookup(item, models, *, keep_ist):
    model = next(
        (
            m
            for m in models
            if m['name'].casefold() == str(item.get('name', '')).casefold()
            and m['category'] == item.get('category')
            and matches_cohort(item, m)
        ),
        None,
    )
    if model is None:
        return None
    result = {
        'verdict': 'check',
        'band': None,
        'upper_bound_ist': None,
        'reference_band': model['reference_band'],
        'deciding': model['deciding'],
    }
    reference_only = model.get('reference_only', False)
    values, labels, selected_shortfalls = [], [], []
    for prop, points in model['axes'].items():
        spec = model['deciding'][prop]
        if spec.get('base_code') and item.get('base_code') != spec['base_code']:
            return (
                None
                if reference_only and 'guide_floor' not in spec
                else result | {'reason': 'unverified base for deciding roll: ' + spec.get('label', prop)}
            )
        value = item.get('properties', {}).get(prop)
        # Some market labels omit class restrictions. Use the model's verified
        # native identity for captures without creating a global skill alias.
        if prop not in item.get('properties', {}):
            value = item.get('native_rolls', {}).get(spec.get('native_key'))
        if value is None and 'price_split' in spec:
            # A listing that does not state a split roll keeps its name band, as without the model.
            return None
        if not numeric(value) or not spec['min'] <= value <= spec['max']:
            return (
                None
                if reference_only and 'guide_floor' not in spec
                else result | {'reason': 'unreadable or out-of-range deciding roll: ' + spec.get('label', prop)}
            )
        best = spec['min'] if spec.get('better') == 'lower' else spec['max']
        floor = spec.get('guide_floor')
        if floor is not None:
            shortfall = value > floor if spec.get('better') == 'lower' else value < floor
            if shortfall:
                selected_shortfalls.append(f'{spec.get("label", prop)} {value:g}, guide trade threshold {floor:g}')
        elif (
            value > spec.get('selection_floor', best)
            if spec.get('better') == 'lower'
            else value < spec.get('selection_floor', best)
        ):
            selected_shortfalls.append(
                f'below listed roll quartile {spec.get("selection_floor", best):g} '
                f'{spec.get("label", prop)}; this has {value:g}'
            )
        oriented = value * (-1 if spec.get('better') == 'lower' else 1)
        values.append(points[bisect_right(points, oriented) - 1])
        labels.append(f'{spec.get("label", prop)} {value:g}')
    cell = model['cells'][key(values)]
    band, ceiling = cell['band'], cell['upper_bound_ist']
    comparison = ', '.join(labels)
    if reference_only:
        if selected_shortfalls:
            return result | {
                'reason': '; '.join(selected_shortfalls) + '; name band is reference only',
            }
        return None
    if band is not None and band['sellers'] < 3:
        return result | {
            'comparison_band': band,
            'reason': (
                f'only {band["sellers"]} comparable-or-worse sellers for {comparison}; name band is reference only'
            ),
        }
    result.update(cell)
    if band is not None:
        price = band['q1_ist']
        verdict = 'vendor' if price < keep_ist else ('sell' if band['liquidity'] == 'liquid' else 'slow')
        return result | {'verdict': verdict, 'reason': f'comparable-or-worse asks for {comparison}'}
    if ceiling is not None:
        return result | {
            'verdict': 'vendor' if ceiling < keep_ist else 'check',
            'reason': f'below listed rolls ({comparison}); cheapest ask {ceiling:g} Ist is an upper bound',
        }
    return result | {'reason': f'no comparable-or-worse listings for {comparison}'}
