"""Demand qualification from completed offline measurements, never seller count alone."""


def qualify(verdict, price, guide_use, observation):
    if verdict not in ('sell', 'slow') or price is None:
        return verdict, None
    observation = observation or {}
    signal = bool(guide_use or observation.get('buyers', 0) or observation.get('uncensored_disappeared', 0))
    measured = observation.get('previous_listings', 0) > 0 and 'current_listings' in observation
    if price < 1:
        if measured and not signal:
            return 'vendor', 'no build use, turnover or observed buyers'
        return 'slow', 'sub-1-Ist equipment; demand supported' if signal else 'demand not established'
    if verdict == 'sell' and not signal:
        return 'slow', 'no build use, turnover or observed buyers'
    return verdict, None


def lookup(item, result, tables):
    from pricing.triage.engine import variant_name_band
    from pricing.triage.listing_scores import cohort_key

    evidence = tables.get('market_demand')
    if not evidence or not evidence.get('complete'):
        return None
    cohort = variant_name_band(item, tables) if item['category'] in ('uniques', 'sets', 'runewords') else None
    key = cohort_key(item, result, cohort, tables)
    observed = evidence['cohorts'].get(key)
    buyer = evidence.get('buyers', {}).get(key)
    return (observed or {}) | (buyer or {}) if observed is not None or buyer is not None else None


def compile_evidence(report):
    if report is None:
        return {'complete': False, 'cohorts': {}, 'buyers': {}}
    return {
        'complete': bool(report['compared_boards'])
        and not report['unobserved_boards']
        and not report['invalid_intervals'],
        'before': report['before'],
        'after': report['after'],
        'cohorts': report['cohorts'],
        'buyers': report.get('buyers', {}).get('cohorts', {}),
        'interpretation': report['interpretation'],
    }


def agreement(verdicts, report):
    """Measure priced cohorts; unmeasured SELL cohorts remain in the denominator."""
    report = report or {}
    cohorts, buyers = report.get('cohorts', {}), report.get('buyers', {}).get('cohorts', {})
    sells = {key for key, values in verdicts.items() if 'sell' in values}
    vendors = {key for key, values in verdicts.items() if 'vendor' in values}
    supported, strong = set(), set()
    for key in sells | vendors:
        observed, bid = cohorts.get(key, {}), buyers.get(key, {})
        if observed.get('uncensored_disappeared', 0) or bid.get('buyers', 0):
            supported.add(key)
        old, gone = observed.get('previous_listings', 0), observed.get('uncensored_disappeared', 0)
        if (gone >= 3 and old > 0 and gone / old >= 0.2) or bid.get('buyers', 0) >= 3:
            strong.add(key)
    return {
        'sell_cohorts': len(sells),
        'sell_supported_share': len(sells & supported) / len(sells) if sells else None,
        'sell_supported_only_by_censored_absence': sum(
            cohorts.get(key, {}).get('disappeared', 0) > 0
            and not cohorts.get(key, {}).get('uncensored_disappeared', 0)
            and not buyers.get(key, {}).get('buyers', 0)
            for key in sells
        ),
        'sell_unmeasured': sorted(sells - cohorts.keys() - buyers.keys()),
        'vendor_cohorts': len(vendors),
        'vendor_strong_share': len(vendors & strong) / len(vendors) if vendors else None,
        'vendor_strong_cohorts': sorted(vendors & strong),
        'strong_cohorts': len(strong),
        'strong_definition': 'At least 3 uncensored disappearances and 20% of old listings, or 3 independent buyers.',
        'interpretation': 'Only uncensored disappearances or scoped buyers support demand; neither proves a sale.',
    }
