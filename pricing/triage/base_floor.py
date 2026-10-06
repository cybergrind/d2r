"""Last-resort plain-base asking floor, preserving identity and socket state."""

import json

from inventory_tracking.items.metadata import metadata_generation
from pricing.triage.market_bases import clean_modifiers


def key(item, base, *, ordinary=False):
    ed = item.get('base_ed')
    if (
        item.get('category') != 'base'
        or (ed is not None and (type(ed) not in (int, float) or not 0 <= ed <= 15))
        or item.get('rarity') not in ('normal', 'superior')
        or type(item.get('ethereal')) is not bool
        or type(item.get('sockets')) is not int
        or not 0 <= item['sockets'] <= base.get('max_sockets', 0)
        or item.get('socket_contents') != 'empty'
        or not clean_modifiers(item, base, {})
    ):
        return None
    dropped = {'937'} if item['rarity'] == 'superior' else set()
    if item['rarity'] == 'superior' and base['category'] == 'weapons':
        dropped.add('423')
    facets = {k: item[k] for k in ('rarity', 'ethereal', 'sockets')}
    facets['base_ed'] = ed
    if ordinary:
        facets['rarity'] = 'normal'
    facets['base_modifiers'] = {p: v for p, v in item['base_modifiers'].items() if p not in dropped}
    return 'base-floor:' + json.dumps(facets, sort_keys=True, separators=(',', ':'))


def targets(item, base, policy=None):
    """Compile shield floors only toward equal or better native rolls."""
    from pricing.triage.base_comparisons import no_worse_modifiers, with_rolls

    modifiers = item.get('base_modifiers', {})
    resistance = modifiers.get('441')
    if base['type'] == 'ashd' and type(resistance) is int and 5 <= resistance <= 45:
        for value in range(resistance, 46):
            yield item | {'base_modifiers': with_rolls(modifiers, {'441': value})}
    elif base['type'] == 'ashd' and {'510', '423'} <= modifiers.keys():
        # Both native damage and AR must dominate the source. Reuse the
        # reviewed bounds instead of mixing resistance and damage automods.
        bounds = (policy or {}).get('compare_inherent', {})
        comparison = {'compare_inherent': {p: bounds[p] for p in ('510', '423') if p in bounds}}
        for target in no_worse_modifiers(item, comparison):
            yield item | {'base_modifiers': target}
    else:
        # Other modifiers remain exact; missing rolls are never guessed as zero.
        yield item


def pooled_key(item, base, *, target_ed=None):
    """Both qualities may support a superior target's floor; never an ordinary target."""
    bucket = key(item, base, ordinary=True)
    if not bucket:
        return None
    facets = json.loads(bucket.removeprefix('base-floor:'))
    if target_ed is not None:
        facets['base_ed'] = target_ed
    return 'base-floor-pooled:' + json.dumps(facets, sort_keys=True, separators=(',', ':'))


def lookup(item, bands, *, keep_ist):
    from pricing.triage.adapters import bases_by_code
    from pricing.triage.named_fallback import supported

    base = bases_by_code(metadata_generation()).get(item.get('base_code'))
    if not base or (bucket := key(item, base)) is None:
        return None
    ed = item.get('base_ed')
    rolls = list(range(ed, -1, -1)) if type(ed) is int and 0 <= ed <= 15 else [ed]
    if ed is None and item['rarity'] == 'superior':
        # Unknown ED has a known lower bound of zero. This admits an ordinary
        # floor without assigning a roll to the target or borrowing a premium.
        rolls = [0, None]
    candidates = []
    for roll in rolls:
        target = item | {'base_ed': roll}
        buckets = [key(target, base)]
        if item['rarity'] == 'superior':
            # Only the superior target can borrow normal quality. Native
            # staffmod identities and rolls stay in each lookup key.
            buckets.append(key(target, base, ordinary=True))
        for bucket in buckets:
            candidates.append((bucket, ed is None or roll != ed))
    if item['rarity'] == 'superior':
        candidates.append((pooled_key(item, base), True))
    for bucket, relaxed in candidates:
        band = bands.get(('base', item['name'].casefold(), bucket))
        # Low floors cannot establish that additional rolls are worthless.
        if supported(band) and band['q1_ist'] >= keep_ist:
            return band | {'relaxed_facets': ['base_ed'] if relaxed else []}
    return None
