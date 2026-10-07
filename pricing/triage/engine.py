"""Table-only drop/listing triage. No roles, exact cohort gate or detail publication."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

from pricing.triage.bands import ethereal_bucket, quantity_bucket
from pricing.triage.commodity_lots import (
    accumulation,
    compile_lots,
    crafting_reason,
    fungible,
    sale_lot,
    sale_value,
    saving_reason,
    sparse_supply_quote,
)
from pricing.triage.compiled_rolls import lookup as roll_model
from pricing.triage.family_bands import lookup as family_band
from pricing.triage.named_fallback import NAMED, lookup as named_fallback, protects_variant, supported
from pricing.triage.patterns import check_reason, matched_patterns
from pricing.triage.rule_index import candidates as rule_candidates, compile_index
from pricing.triage.socket_potential import preparation
from pricing.triage.variants import base_bucket, profile_for, scoped_bucket, socket_bucket


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


def variant_name_band(item, tables):
    category, name = item.get('category'), str(item.get('name', '')).casefold()
    bucket = quantity_bucket(item.get('quantity', 1))
    reference = tables['bands'].get((category, name, bucket)) or {}
    if 'named_cohorts' in reference:
        from pricing.triage.named_cohorts import lookup as cohort_band

        return cohort_band(item, reference)
    facets = profile_for(item, tables['rules'].get('policies', [])).get('facets', [])
    if not facets and reference.get('separate_ethereal'):
        bucket = ethereal_bucket(bucket, item.get('ethereal'))
    bucket = scoped_bucket(bucket, item, facets)
    if reference.get('separate_sockets'):
        bucket = socket_bucket(bucket, item)
    if reference.get('separate_base'):
        bucket = base_bucket(bucket, item)
    return tables['bands'].get((category, name, bucket))


def assess(item, tables, *, today=None):
    today = today or datetime.now(UTC).date()
    rows = rule_candidates(item, tables['rule_index']) if 'rule_index' in tables else tables['rules']['rows']
    rules = [r for r in rows if matches(item, r)]
    category, name = item.get('category'), str(item.get('name', '')).casefold()
    name_bucket = quantity_bucket(item.get('quantity', 1))
    reference = tables['bands'].get((category, name, name_bucket))
    policy = profile_for(item, tables['rules'].get('policies', []))
    facets = policy.get('facets', [])
    separate = not facets and (reference or {}).get('separate_ethereal', False)
    separate_sockets = (reference or {}).get('separate_sockets', False)
    separate_base = (reference or {}).get('separate_base', False)
    candidates = [r['bucket'] for r in rules if r.get('bucket')]
    if policy.get('require_bucket'):
        candidates = candidates[:1]
    if not policy.get('require_bucket'):
        candidates.append(name_bucket)
    band, bucket = None, name_bucket
    for candidate in candidates:
        bucket = ethereal_bucket(candidate, item.get('ethereal')) if separate else candidate
        bucket = scoped_bucket(bucket, item, facets)
        if separate_sockets:
            bucket = socket_bucket(bucket, item)
        if separate_base:
            bucket = base_bucket(bucket, item)
        found = tables['bands'].get((category, name, bucket)) if bucket is not None else None
        if category == 'base' and candidate != name_bucket:
            from pricing.triage.base_cohorts import band as base_cohort

            props = next((r.get('properties', {}) for r in rules if r.get('bucket') == candidate), {})
            coarse = base_cohort(item, candidate, policy, tables['bands'], props)
            if coarse and coarse.get('sellers', 0) >= 3:
                found, bucket = coarse, coarse['bucket']
        # Keep sparse base-variant bands for CHECK; never borrow another variant.
        # Other specific bands require three sellers or an explicit comparison,
        # otherwise fall back through the remaining compatible candidates.
        if (
            found is not None
            and found.get('median_ist') is not None
            and (
                candidate == name_bucket
                or found.get('sellers', 0) >= 3
                or found.get('comparison')
                or category == 'base'
            )
        ):
            band = found
            break
    if category == 'base' and not supported(band):
        from pricing.triage.base_fallback import lookup as base_fallback

        if fallback := base_fallback(item, tables['bands'], keep_ist=tables['rules']['keep_ist']):
            band, bucket = fallback, fallback['bucket']
    # Arbitrary affixed names cannot borrow a generic Ring/Amulet market band.
    if category in ('magic', 'rare', 'crafted'):
        band, reference = family_band(item, rules, tables['bands'])
        bucket = band['bucket'] if band else None
    sale_mode = None
    quantity = item.get('quantity', 1)
    if (
        fungible(item)
        and type(quantity) is int
        and quantity > 1
        and (band or {}).get('liquidity') not in ('liquid', 'thin')
    ):
        single = tables['bands'].get((category, name, 'name'))
        if single and single.get('liquidity') in ('liquid', 'thin') and single.get('q1_ist') is not None:
            # Fungible units can be sold separately. Keep the lot's band as
            # reference; never label the single-unit quote a bulk estimate.
            reference, band, bucket, sale_mode = reference, single, 'name', 'individual'
    premium = any(r.get('premium') is True for r in rules)
    pattern_rows = (
        rule_candidates(item, tables['pattern_index']) if 'pattern_index' in tables else tables['rules']['rows']
    )
    socket_preparation = preparation(item, tables['rules'])
    patterns = matched_patterns(item, pattern_rows, socket_preparation=socket_preparation)
    if (reference or {}).get('named_cohorts') is not None:
        from pricing.triage.named_cohorts import lookup as cohort_band

        band = cohort_band(item, reference)
        if (
            band
            and band.get('cohort_depth', 0) == 0
            and protects_variant(
                item, band | {'variant_prices': reference['variant_prices']}, tables['rules']['keep_ist']
            )
        ):
            band = None
        if band is None:
            band = named_fallback(item, tables, [], allow_name=False)
        bucket = band['bucket'] if band else None
    elif category in NAMED and not supported(band):
        fallback = named_fallback(
            item, tables, candidates, allow_name=not policy.get('require_bucket') or bool(patterns)
        )
        if fallback:
            band, bucket = fallback, fallback['bucket']
    price = (band or {}).get('q1_ist', (band or {}).get('median_ist'))
    if fungible(item) and type(quantity) is int and quantity > 1 and (band or {}).get('quantity') == quantity:
        price = sale_value(item, price)
        sale_mode = 'bulk'
    liquidity = (band or {}).get('liquidity', 'none')
    if premium and price is not None and not supported(band):
        verdict, reason = 'check', 'premium pattern with sparse asks; price is reference only'
    elif premium:
        verdict, reason = 'sell', 'premium rule combination'
    elif price is not None and price >= tables['rules']['keep_ist'] and liquidity in ('liquid', 'thin'):
        verdict, reason = ('sell' if liquidity == 'liquid' else 'slow'), f'asks {price:g} Ist lower quartile'
    elif (
        (category in NAMED or category == 'base')
        and supported(band)
        and price is not None
        and price < tables['rules']['keep_ist']
    ):
        verdict, reason = 'vendor', 'below keep price'
    elif patterns:
        verdict, reason = 'check', min((check_reason(item, r) for r in patterns), key=len)
    elif (
        category in ('magic', 'rare', 'crafted')
        and price is not None
        and price >= tables['rules']['keep_ist']
        and 0 < (band or {}).get('sellers', 0) < 3
    ):
        verdict, reason = 'check', 'fewer than three sellers for the matched stat pattern; price is reference only'
    elif price is not None and price >= tables['rules']['keep_ist'] and (band or {}).get('comparison'):
        verdict, reason = 'check', 'fewer than three comparable-or-worse sellers'
    elif (
        category == 'base'
        and any(r.get('bucket') for r in rules)
        and price is not None
        and price >= tables['rules']['keep_ist']
    ):
        verdict, reason = 'check', 'fewer than three sellers for the matched base variant; price is reference only'
    elif any(matches(item, r) for r in tables['own']['rows']):
        verdict, reason = 'self', 'own-build rule'
    else:
        verdict, reason = (
            'vendor',
            'no listings'
            if price is None
            else 'below keep price'
            if price < tables['rules']['keep_ist']
            else 'insufficient price evidence',
        )
    if category == 'base' and verdict == 'vendor' and not supported(band):
        from pricing.triage.base_fallback import missing_reason

        if missing := missing_reason(item, rows):
            verdict, reason = 'check', missing
    if verdict == 'vendor' and price is None and (facets or policy.get('require_bucket')):
        reason = 'no priced band for the required base, variant or roll combination'
    if verdict == 'vendor' and price is None and (separate or separate_sockets or separate_base):
        required = [
            (field, label)
            for enabled, field, label in (
                (separate_base, 'base_code', 'base'),
                (separate, 'ethereal', 'ethereal status'),
                (separate_sockets, 'sockets', 'sockets'),
                (separate_sockets, 'socket_contents', 'socket contents'),
            )
            if enabled
        ]
        missing = [label for field, label in required if item.get(field) in (None, 'unknown')]
        reason = (
            f'capture missing {", ".join(missing)}; variant price unavailable'
            if missing
            else 'no priced listings matching base, ethereal status and sockets'
        )
    if verdict == 'vendor':
        reason = next((r['default_reason'] for r in rules if r.get('default_reason')), reason)
        if lot := sale_lot(item, tables):
            reference, band = band, lot
            price, liquidity = lot['q1_ist'] * lot['quantity'], lot['liquidity']
            bucket, sale_mode = quantity_bucket(lot['quantity']), 'split_bulk'
            verdict = 'sell' if liquidity == 'liquid' else 'slow'
            reason = f'sell in lots of {lot["quantity"]}'
        elif lot := accumulation(item, tables):
            verdict, reason, sale_mode = 'check', saving_reason(lot), 'accumulate'
            reference, band, price, bucket, liquidity = lot, None, None, None, 'none'
        elif recipe := crafting_reason(item):
            verdict, reason = 'check', recipe
        elif quote := sparse_supply_quote(item, tables, band, price):
            verdict, reason = 'check', 'fewer than three sellers for this commodity lot; price is reference only'
            if quote.get('quantity', 1) != item.get('quantity', 1):
                reason = 'only sparse unit asks; stack price unavailable'
            band, price, bucket = quote, quote['q1_ist'], quote['bucket']
    comparison = roll_model(item, tables.get('roll_models', []), keep_ist=tables['rules']['keep_ist'])
    if comparison is not None:
        verdict, reason = comparison['verdict'], comparison['reason']
        band, reference = comparison['band'], comparison['reference_band']
        bucket = 'roll-comparison'
        price = band['q1_ist'] if band else None
        liquidity = band['liquidity'] if band else 'none'
    if category in ('uniques', 'sets', 'runewords') and comparison is None and verdict == 'vendor':
        if price is None:
            verdict = 'check'
            reason += '; name band is reference only' if reference else '; no cached price evidence'
        elif (band or {}).get('sellers', 0) < 3:
            verdict, reason = 'check', 'fewer than three comparable sellers; price is reference only'
    if label := (band or {}).get('comparison', {}).get('label'):
        reason += f' · comparable-or-worse {label}'
    from pricing.triage.named_roll_placement import lookup as roll_placement, ordinary_has_demand

    placement = roll_placement(item, tables.get('named_roll_placements', []))
    if placement:
        reason = placement['reason']
        if not placement['valid']:
            verdict, band, price, liquidity = 'check', None, None, 'none'
        else:
            band = placement['band']
            price, bucket, liquidity = band['q1_ist'], band['bucket'], band['liquidity']
            verdict = 'vendor' if price < tables['rules']['keep_ist'] else 'sell' if liquidity == 'liquid' else 'slow'
    own_use = next((r for r in tables['own']['rows'] if matches(item, r)), None)
    if own_use and (
        verdict in ('vendor', 'self')
        or (verdict == 'check' and category in NAMED and price is None and not patterns and comparison is None)
    ):
        verdict, reason = 'self', own_use.get('label', 'own-build rule')
    from pricing.triage.demand import demand_for

    demand = demand_for(item, tables.get('demand', {}))
    market_demand = None
    if tables.get('market_demand', {}).get('complete') and not fungible(item):
        from pricing.triage.market_demand import lookup, qualify

        market_demand = lookup(item, {'band': band, 'preparation': socket_preparation}, tables)
        verdict, qualification = qualify(verdict, price, bool(demand or own_use), market_demand)
        if qualification:
            reason = qualification
    elif verdict in ('sell', 'slow') and price is not None and price < 1 and not fungible(item):
        from pricing.triage.market_demand import qualify

        verdict, reason = qualify(verdict, price, bool(demand or own_use), None)
    if placement and placement['valid']:
        reason = placement['reason']
        if placement['group'] == 'ordinary' and placement['ordinary_floor']:
            verdict = (
                'slow'
                if price >= tables['rules']['keep_ist'] and ordinary_has_demand(placement, market_demand)
                else 'vendor'
            )
    if own_use and verdict == 'vendor':
        verdict, reason = 'self', own_use.get('label', 'own-build rule')
    if verdict in ('vendor', 'self') and tables.get('learned_index'):
        from pricing.triage.learned_patterns import lookup as learned_pattern

        if learned := learned_pattern(item, tables['learned_index']):
            reference = learned['reference_band']
            verdict = 'check'
            reason = (
                f'listed stat combination; reference asks {reference["q1_ist"]:g} Ist lower quartile'
                f' · {reference["sellers"]} sellers · {reference["observed_at"]}'
            )
            band, price, bucket, liquidity = None, None, None, 'none'
    # Steering 13: paid-property models remain offline diagnostics until validated.
    if verdict == 'vendor' and reason == 'no listings' and category in ('magic', 'rare', 'crafted'):
        from pricing.triage.patterns import vendor_reason

        reason = vendor_reason(item, pattern_rows)
    if category == 'affixed_unknown':
        from pricing.triage.unknown_affixed import review_pattern

        matched = review_pattern(item, tables)
        verdict = 'check' if matched else 'vendor'
        reason = 'rarity unreported; ' + (matched or 'no reviewed trade combination for the reported stats')
        band, reference, price, bucket, liquidity = None, None, None, None, 'none'
    try:
        stale = (today - date.fromisoformat(band['observed_at'][:10])).days > 45
    except TypeError, KeyError, ValueError:
        stale = None
    sparse_quote = verdict == 'check' and price is not None and not supported(band)
    if sparse_quote:
        # Sparse asks explain why an item needs review; they do not establish
        # its price. Keep the actual matched quote, rather than a pooled name.
        reference, band, price, liquidity = band, None, None, 'none'
    return {
        'verdict': verdict,
        'reason': reason,
        'band': band,
        'reference_band': reference
        if sparse_quote
        or category in NAMED
        or sale_mode
        or comparison is not None
        or category in ('magic', 'rare', 'crafted')
        or separate
        or separate_sockets
        or facets
        or policy.get('require_bucket')
        else None,
        'bucket': bucket,
        'stale': stale,
        'liquidity': liquidity,
        'keep_ist': tables['rules']['keep_ist'],
        'decision_ist': price,
        'roll_comparison': comparison,
        'roll_placement': placement,
        'preparation': socket_preparation,
        'sale_mode': sale_mode,
        'own_use': own_use,
        'demand': demand,
        'market_demand': market_demand,
    }


def revision(directory=DATA):
    return tuple(
        (p.stat().st_mtime_ns, p.stat().st_size)
        for p in (Path(directory) / f'{name}.json' for name in ('bands', 'rules', 'own'))
    )


def prepare_rules(data, rules):
    return data | {
        'rules': rules,
        'rule_index': compile_index(rules['rows']),
        'pattern_index': compile_index(rules['rows'], patterns=True),
        'commodity_lots': compile_lots(data['bands'], rules['keep_ist']),
    }


def prepare_tables(bands, rules, own):
    data = {
        'bands': {(b['category'], b['name'].casefold(), b['bucket']): b for b in bands['bands']},
        'own': own,
        'roll_models': bands.get('roll_models', []),
        'named_roll_placements': bands.get('named_roll_placements', []),
        'demand': bands.get('demand', {}),
        'market_demand': bands.get('market_demand', {}),
        'base_socket_inferences': bands.get('base_socket_inferences', {}),
        'learned_index': compile_index(bands.get('learned_patterns', [])),
    }
    return prepare_rules(data, rules)


class Tables:
    def __init__(self, directory=DATA):
        self.directory = Path(directory)
        self.stamp = None
        self.data = None

    def load(self):
        paths = [self.directory / f'{name}.json' for name in ('bands', 'rules', 'own')]
        stamp = revision(self.directory)
        if stamp != self.stamp:
            if self.stamp is not None and stamp[0] == self.stamp[0]:
                # Build a replacement before publishing; failed reads must leave
                # the old snapshot and revision intact for a later retry.
                data = self.data
                if stamp[1] != self.stamp[1]:
                    data = prepare_rules(data, json.loads(paths[1].read_text()))
                if stamp[2] != self.stamp[2]:
                    data = data | {'own': json.loads(paths[2].read_text())}
                self.data = data
            else:
                bands, rules, own = [json.loads(p.read_text()) for p in paths]
                self.data = prepare_tables(bands, rules, own)
            self.stamp = stamp
        return self.data
