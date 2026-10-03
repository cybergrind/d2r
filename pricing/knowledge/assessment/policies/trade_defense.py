"""Reviewed total-defense representation for Trang-Oul's Girth.

Item stat31 includes the rolled armor base plus the flat item bonus. Market1855
is explicitly total Defense; market399 is a separate bonus, never a fallback.
The original belt cannot socket or roll ethereal. Its conditional item property
is cold resistance; total mana/defense outside the item bounds cannot qualify.
"""

from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.market_base_catalog import equipment_base


MODE = 'trang_girth'


def girth_bounds(facts, *, captured=True):
    if (
        (facts.rarity, facts.name) != ('set', "Trang-Oul's Girth")
        or facts.identified is not True
        or facts.ethereal is not False
        or type(facts.sockets) is not int
        or facts.sockets != 0
        or facts.socket_contents != 'empty'
        or facts.gaps
        or (captured and facts.capture_complete is not True)
        or any(key in facts.stats for key in ('16:0', '214:0', '215:0'))
    ):
        return None
    definition, errors = resolve_named_definition(facts, identity_only=True)
    if errors or definition is None or facts.base_code not in definition['base_codes']:
        return None
    # This proof is specific to the reviewed original belt and its native tables.
    if any(value != 'res-cold' for key, value in definition['game_definition'].items() if key.startswith('aprop')):
        return None
    base = equipment_base(definition['base_name'])
    flat = definition['roll_ranges'].get('31', {})
    if not base or base[0]['base_code'] != facts.base_code or base[0]['details'].get('max_sockets') != 0:
        return None
    native = base[0]['details'].get('base_defense', ())
    bonus = (flat.get('min'), flat.get('max'))
    if (
        len(native) != 2
        or flat.get('property') != 'ac'
        or any(type(v) is not int or v < 0 for v in (*native, *bonus))
        or native[0] > native[1]
        or bonus[0] > bonus[1]
    ):
        return None
    return native, bonus


def valid_total_defense(facts, *, market_properties=None):
    bounds = girth_bounds(facts, captured=market_properties is None)
    row = facts.stats.get('31:0', {})
    total = row.get('value')
    if bounds is None or row.get('status') != 'decoded' or type(total) is not int:
        return False
    native, bonus = bounds
    if not native[0] + bonus[0] <= total <= native[1] + bonus[1]:
        return False
    if market_properties is not None and '399' in market_properties:
        flat = market_properties['399']
        if type(flat) is not int or not bonus[0] <= flat <= bonus[1] or not native[0] <= total - flat <= native[1]:
            return False
    return True
