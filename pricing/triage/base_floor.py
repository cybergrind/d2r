"""Last-resort plain-base asking floor, preserving identity and socket state."""

import json

from inventory_tracking.items.metadata import metadata, metadata_generation
from pricing.triage.market_bases import clean_modifiers


def key(item, base, *, ordinary=False):
    ed = item.get('base_ed')
    if (
        item.get('category') != 'base'
        or (ed is not None and (type(ed) not in (int, float) or not 0 <= ed <= 15))
        or base['type'] in metadata()['staffmods']['classes_by_type']
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
    if base['type'] == 'ashd':
        dropped.update(('441', '401', '426', '427', '428', '510', '423'))
    facets = {k: item[k] for k in ('rarity', 'ethereal', 'sockets')}
    if ordinary:
        facets['rarity'] = 'normal'
    facets['base_modifiers'] = {p: v for p, v in item['base_modifiers'].items() if p not in dropped}
    return 'base-floor:' + json.dumps(facets, sort_keys=True, separators=(',', ':'))


def pooled_key(item, base):
    """Both qualities may support a superior target's floor; never an ordinary target."""
    bucket = key(item, base, ordinary=True)
    return bucket.replace('base-floor:', 'base-floor-pooled:', 1) if bucket else None


def lookup(item, bands, *, keep_ist):
    from pricing.triage.adapters import bases_by_code
    from pricing.triage.named_fallback import supported

    base = bases_by_code(metadata_generation()).get(item.get('base_code'))
    if not base or (bucket := key(item, base)) is None:
        return None
    band = bands.get(('base', item['name'].casefold(), bucket))
    # A low floor cannot establish that the item's additional rolls are worthless.
    if supported(band) and band['q1_ist'] >= keep_ist:
        return band
    if item['rarity'] == 'superior':
        # Additional superior bonuses cannot remove an ordinary base's use.
        # This direction is intentional: ordinary copies never borrow premiums.
        bucket = key(item, base, ordinary=True)
        band = bands.get(('base', item['name'].casefold(), bucket))
        if supported(band) and band['q1_ist'] >= keep_ist:
            return band
        band = bands.get(('base', item['name'].casefold(), pooled_key(item, base)))
        if supported(band) and band['q1_ist'] >= keep_ist:
            return band
    return None
