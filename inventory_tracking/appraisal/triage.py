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


def price_description(triage):
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
    if triage.get('sale_mode') in ('bulk', 'split_bulk'):
        sellers = band['sellers']
        preparation = f'sell in lots of {quantity} · ' if triage['sale_mode'] == 'split_bulk' else ''
        return (
            f'{preparation}asks {price * quantity:.3g} Ist {statistic} per lot of {quantity} '
            f'({price:.3g} Ist each) · {sellers} sellers · {observed}{stale}'
        )
    lot = (
        ' each; sell individually'
        if triage.get('sale_mode') == 'individual'
        else f' each in lots of {quantity}'
        if quantity > 1
        else ''
    )
    comparison = f' · {triage["reason"]}' if triage.get('roll_comparison') else ''
    if label := band.get('comparison', {}).get('label'):
        comparison = f' · comparable-or-worse {label}'
    unsupported = triage['verdict'] == 'vendor' and price >= triage.get('keep_ist', 0.25)
    prefix = f'{triage["reason"]} · reference ' if unsupported else ''
    sellers = band['sellers']
    seller_label = 'seller' if sellers == 1 else 'sellers'
    return f'{prefix}asks {price:g} Ist {statistic}{lot} · {sellers} {seller_label} · {observed}{stale}{comparison}'


def description(triage):
    text = price_description(triage)
    if options := triage.get('preparation'):
        counts = '/'.join(str(n) for n in options['larzuk'])
        conditional = ' (item level unknown)' if options['conditional'] else ''
        text += f' · Larzuk: {counts} sockets{conditional}'
        if cube := options['cube']:
            count = str(cube[-1]) if len(cube) == 1 else f'1-{cube[-1]}'
            text += f' · cube: {count} sockets'
    return text


def headline(triage):
    return f'{LABELS[triage["verdict"]]} — {description(triage)}'
