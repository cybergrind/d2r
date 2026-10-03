"""Table-only drop/listing triage. No roles, exact cohort gate or detail publication."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

from pricing.triage.bands import ethereal_bucket, quantity_bucket
from pricing.triage.compiled_rolls import lookup as roll_model
from pricing.triage.family_bands import lookup as family_band
from pricing.triage.patterns import check_reason, matched_patterns
from pricing.triage.variants import profile_for, scoped_bucket


DATA = Path(__file__).resolve().parents[1] / 'data/triage'


def matches(item, rule):
    for key in ('category', 'name', 'family'):
        if key in rule and str(item.get(key, '')).casefold() != str(rule[key]).casefold():
            return False
    for field, conditions in (
        (item, rule.get('conditions', {})),
        (item.get('properties', {}), rule.get('properties', {})),
    ):
        for key, condition in conditions.items():
            value = field.get(key)
            if value is None:
                return False
            if not isinstance(condition, dict):
                if value != condition or type(value) is not type(condition):
                    return False
                continue
            if not condition or set(condition) - {'in', 'min', 'max'}:
                return False
            if 'in' in condition and value not in condition['in']:
                return False
            for bound, compare in (('min', lambda a, b: a >= b), ('max', lambda a, b: a <= b)):
                if bound in condition and (type(value) not in (int, float) or not compare(value, condition[bound])):
                    return False
    if 'at_least' in rule:
        group = rule['at_least']
        if not isinstance(group, dict) or set(group) != {'count', 'of'}:
            return False
        count, options = group['count'], group['of']
        if type(count) is not int or count < 1 or not isinstance(options, list):
            return False
        if any(not isinstance(option, dict) or not option for option in options):
            return False
        unique = {json.dumps(option, sort_keys=True): option for option in options}
        if sum(matches(item, option) for option in unique.values()) < count:
            return False
    return True


def assess(item, tables, *, today=None):
    today = today or datetime.now(UTC).date()
    rules = [r for r in tables['rules']['rows'] if matches(item, r)]
    category, name = item.get('category'), str(item.get('name', '')).casefold()
    name_bucket = quantity_bucket(item.get('quantity', 1))
    reference = tables['bands'].get((category, name, name_bucket))
    policy = profile_for(item, tables['rules'].get('policies', []))
    facets = policy.get('facets', [])
    separate = not facets and (reference or {}).get('separate_ethereal', False)
    candidates = [r['bucket'] for r in rules if r.get('bucket')]
    if policy.get('require_bucket'):
        candidates = candidates[:1]
    if not policy.get('require_bucket'):
        candidates.append(name_bucket)
    band, bucket = None, name_bucket
    for candidate in candidates:
        bucket = ethereal_bucket(candidate, item.get('ethereal')) if separate else candidate
        bucket = scoped_bucket(bucket, item, facets)
        found = tables['bands'].get((category, name, bucket)) if bucket is not None else None
        # A specific roll band needs three sellers; otherwise use the broader
        # name band, retaining the ethereal distinction whenever it is material.
        if (
            found is not None
            and found.get('median_ist') is not None
            and (candidate == name_bucket or found.get('sellers', 0) >= 3)
        ):
            band = found
            break
    # Arbitrary affixed names cannot borrow a generic Ring/Amulet market band.
    if category in ('magic', 'rare', 'crafted'):
        band, reference = family_band(item, rules, tables['bands'])
        bucket = band['bucket'] if band else None
    premium = any(r.get('premium') is True for r in rules)
    patterns = matched_patterns(item, tables['rules']['rows'])
    price = (band or {}).get('q1_ist', (band or {}).get('median_ist'))
    liquidity = (band or {}).get('liquidity', 'none')
    if premium:
        verdict, reason = 'sell', 'premium rule combination'
    elif price is not None and price >= tables['rules']['keep_ist'] and liquidity in ('liquid', 'thin'):
        verdict, reason = ('sell' if liquidity == 'liquid' else 'slow'), f'asks {price:g} Ist lower quartile'
    elif patterns:
        verdict, reason = 'check', min((check_reason(item, r) for r in patterns), key=len)
    elif any(matches(item, r) for r in tables['own']['rows']):
        verdict, reason = 'self', 'own-build rule'
    else:
        verdict, reason = (
            'vendor',
            'no listings' if price is None else 'below keep price or insufficient market interest',
        )
    if verdict == 'vendor' and price is None and (facets or policy.get('require_bucket')):
        reason = 'no priced band for the required base, variant or roll combination'
    if verdict == 'vendor' and price is None and separate:
        variant = (
            'ethereal'
            if item.get('ethereal') is True
            else 'non-ethereal'
            if item.get('ethereal') is False
            else 'unknown-ethereal'
        )
        reason = f'no {variant} listings; mixed-variant asks excluded'
    if verdict == 'vendor':
        reason = next((r['default_reason'] for r in rules if r.get('default_reason')), reason)
    comparison = roll_model(item, tables.get('roll_models', []), keep_ist=tables['rules']['keep_ist'])
    if comparison is not None:
        verdict, reason = comparison['verdict'], comparison['reason']
        band, reference = comparison['band'], comparison['reference_band']
        bucket = 'roll-comparison'
        price = band['q1_ist'] if band else None
        liquidity = band['liquidity'] if band else 'none'
    try:
        stale = (today - date.fromisoformat(band['observed_at'][:10])).days > 45
    except TypeError, KeyError, ValueError:
        stale = None
    return {
        'verdict': verdict,
        'reason': reason,
        'band': band,
        'reference_band': reference
        if comparison is not None
        or category in ('magic', 'rare', 'crafted')
        or separate
        or facets
        or policy.get('require_bucket')
        else None,
        'bucket': bucket,
        'stale': stale,
        'liquidity': liquidity,
        'keep_ist': tables['rules']['keep_ist'],
        'decision_ist': price,
        'roll_comparison': comparison,
    }


def revision(directory=DATA):
    return tuple(
        (p.stat().st_mtime_ns, p.stat().st_size)
        for p in (Path(directory) / f'{name}.json' for name in ('bands', 'rules', 'own'))
    )


class Tables:
    def __init__(self, directory=DATA):
        self.directory = Path(directory)
        self.stamp = None
        self.data = None

    def load(self):
        paths = [self.directory / f'{name}.json' for name in ('bands', 'rules', 'own')]
        stamp = revision(self.directory)
        if stamp != self.stamp:
            bands, rules, own = [json.loads(p.read_text()) for p in paths]
            self.data = {
                'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in bands['bands']},
                'rules': rules,
                'own': own,
                'roll_models': bands.get('roll_models', []),
            }
            self.stamp = stamp
        return self.data
