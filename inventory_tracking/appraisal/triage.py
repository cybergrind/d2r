"""The same short, dated triage verdict on every presentation surface."""

from inventory_tracking.presentation import Tone


# The trade verdict's words. `sell` and `slow` read TRADE (2026-10-23, R3 of rca/2026-10-23/assess-sites-findings.md):
# the card also shows what the loop would do (CARD_LABELS), and a vendor sale is VENDOR there; "SELL" read as either
LABELS = {'sell': 'TRADE', 'slow': 'TRADE (slow)', 'check': 'CHECK', 'self': 'SELF-USE', 'vendor': 'VENDOR'}
# What the loop would do with the item (loot/assess.py `Outcome` at CARD): kept (stashed), sold to a vendor, ...
CARD_LABELS = {
    'keep': 'KEEP',
    'vendor': 'VENDOR',
    'identify': 'IDENTIFY',
    'never-touch': 'KEEP (untouched)',
    'drop': 'DROP',
    'pick': 'PICK',
    'leave': 'LEAVE',
    'buy': 'BUY',
    'pass': 'PASS',
}
CARD_TONES = {'vendor': Tone.METADATA, 'drop': Tone.METADATA, 'leave': Tone.METADATA}
CARD_WHY = 110  # characters of the entry point's why on the OSD line
TONES = {
    'sell': Tone.TIER_HIGH,
    'slow': Tone.TIER_MED,
    'check': Tone.DEFAULT,
    'self': Tone.TIER_LOW,
    'vendor': Tone.METADATA,
}


def demand_unmeasured(triage):
    return triage.get('verdict') == 'slow' and triage.get('reason') == 'demand unmeasured'


def tone(triage):
    return Tone.DEFAULT if demand_unmeasured(triage) else TONES[triage['verdict']]


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
    comparison = f' · {triage["reason"]}' if triage.get('roll_comparison') or triage.get('roll_placement') else ''
    if label := band.get('comparison', {}).get('label'):
        comparison = f' · comparable-or-worse {label}'
    unsupported = triage['verdict'] == 'vendor' and price >= triage.get('keep_ist', 0.25)
    if unsupported:
        comparison = ''
    prefix = f'{triage["reason"]} · reference ' if unsupported else ''
    if band.get('price_basis') == 'base_floor':
        prefix += 'at least '
    sellers = band['sellers']
    seller_label = 'seller' if sellers == 1 else 'sellers'
    return f'{prefix}asks {price:g} Ist {statistic}{lot} · {sellers} {seller_label} · {observed}{stale}{comparison}'


def description(triage):
    text = price_description(triage)
    if demand_unmeasured(triage) and 'demand unmeasured' not in text:
        text += ' · demand unmeasured'
    if triage.get('ethereal_basis'):
        text += ' · ' + triage['ethereal_basis']
    if triage['verdict'] in ('sell', 'slow') and (own := triage.get('own_use')):
        text += ' · Own use: ' + own.get('label', 'own-build rule')
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


def card_line(card) -> str:
    """The card's line for the entry point's CARD outcome (identify/service.py `card_of`): 'Loop: VENDOR K8 — why'."""
    why = card['why'] if len(card['why']) <= CARD_WHY else card['why'][: CARD_WHY - 1] + '…'
    return f'Loop: {CARD_LABELS.get(card["outcome"], card["outcome"].upper())} {card["rule"]} — {why}'


def card_tone(card):
    return CARD_TONES.get(card['outcome'], Tone.DEFAULT)
