"""Compile roll comparisons offline; runtime only selects a precomputed cell."""

import json
from bisect import bisect_right
from itertools import product

from pricing.triage.adapters import expanded_properties
from pricing.triage.bands import band_for, eligible
from pricing.triage.roll_cohorts import matches_cohort
from pricing.triage.roll_comparisons import comparable, compare, fallback_required, numeric


def key(values):
    return json.dumps(values, separators=(',', ':'))


def compile_model(report, rows, *, require_supported_split=False):
    if not report['deciding'] or fallback_required(report['validation']):
        return None
    cohort = [
        r | {'properties': expanded_properties(r.get('properties', {}))}
        for r in rows
        if eligible(r)
        and r['name'].casefold() == report['name'].casefold()
        and matches_cohort(r, report)
        and r['amount'] == 1
    ]
    if not cohort:
        return None
    deciding = report['deciding']
    if require_supported_split:
        from pricing.triage.cohort_splits import roll_split

        deciding = {
            prop: spec
            for prop, spec in deciding.items()
            if roll_split(cohort, prop)
            or (
                report.get('coarse_facets') is not None
                and spec.get('sample_size', 0) >= 15
                and spec.get('top_count', 0) / spec['sample_size'] >= 0.75
            )
        }
        if not deciding:
            return None
    axes = {}
    for prop, spec in deciding.items():
        sign = -1 if spec.get('better') == 'lower' else 1
        boundary = spec['max'] if sign == -1 else spec['min']
        axes[prop] = sorted(
            {sign * boundary}
            | {
                sign * r['properties'][prop]
                for r in cohort
                if numeric(r['properties'].get(prop)) and spec['min'] <= r['properties'][prop] <= spec['max']
            }
        )
    cells = {}
    for values in product(*axes.values()):
        properties = {
            p: value * (-1 if deciding[p].get('better') == 'lower' else 1)
            for p, value in zip(axes, values, strict=True)
        }
        result = compare(properties, cohort, deciding, keep_ist=0)
        selected = [r for r in cohort if comparable(r, properties, deciding)]
        band = band_for(cohort[0]['category'], report['name'], selected) if result['q1_ist'] is not None else None
        cells[key(values)] = {'band': band, 'upper_bound_ist': result['upper_bound_ist']}
    return {
        **report,
        'deciding': deciding,
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
    values, labels = [], []
    for prop, points in model['axes'].items():
        spec = model['deciding'][prop]
        if spec.get('base_code') and item.get('base_code') != spec['base_code']:
            return result | {'reason': 'unverified base for deciding roll: ' + spec.get('label', prop)}
        value = item.get('properties', {}).get(prop)
        # Some market labels omit class restrictions. Use the model's verified
        # native identity for captures without creating a global skill alias.
        if prop not in item.get('properties', {}):
            value = item.get('native_rolls', {}).get(spec.get('native_key'))
        if not numeric(value) or not spec['min'] <= value <= spec['max']:
            return result | {'reason': 'unreadable or out-of-range deciding roll: ' + spec.get('label', prop)}
        oriented = value * (-1 if spec.get('better') == 'lower' else 1)
        values.append(points[bisect_right(points, oriented) - 1])
        labels.append(f'{spec.get("label", prop)} {value:g}')
    cell = model['cells'][key(values)]
    band, ceiling = cell['band'], cell['upper_bound_ist']
    result.update(cell)
    comparison = ', '.join(labels)
    if band is not None:
        price = band['q1_ist']
        verdict = (
            'check'
            if band['sellers'] < 3
            else 'vendor'
            if price < keep_ist
            else ('sell' if band['liquidity'] == 'liquid' else 'slow')
        )
        return result | {'verdict': verdict, 'reason': f'comparable-or-worse asks for {comparison}'}
    if ceiling is not None:
        return result | {
            'verdict': 'vendor' if ceiling < keep_ist else 'check',
            'reason': f'below listed rolls ({comparison}); cheapest ask {ceiling:g} Ist is an upper bound',
        }
    return result | {'reason': f'no comparable-or-worse listings for {comparison}'}
