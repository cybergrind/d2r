"""The same short, dated triage verdict on every presentation surface."""

from inventory_tracking.presentation import Tone


LABELS = {'sell': 'SELL', 'slow': 'SELL (slow)', 'check': 'CHECK', 'self': 'SELF-USE', 'vendor': 'VENDOR'}
TONES = {
    'sell': Tone.TIER_HIGH,
    'slow': Tone.TIER_MED,
    'check': Tone.DEFAULT,
    'self': Tone.TIER_LOW,
    'vendor': Tone.METADATA,
}


def description(triage):
    if triage['verdict'] == 'check':
        return triage['reason']
    band = triage.get('band') or {}
    price = band.get('q1_ist', band.get('median_ist'))
    statistic = 'lower quartile' if 'q1_ist' in band else 'median'
    if price is None:
        return triage['reason']
    observed = band.get('observed_at') or 'undated'
    stale = ' · stale' if triage.get('stale') else ''
    quantity = band.get('quantity', 1)
    lot = f' each in lots of {quantity}' if quantity > 1 else ''
    comparison = f' · {triage["reason"]}' if triage.get('roll_comparison') else ''
    return f'asks {price:g} Ist {statistic}{lot} · {band["sellers"]} sellers · {observed}{stale}{comparison}'


def headline(triage):
    return f'{LABELS[triage["verdict"]]} — {description(triage)}'
