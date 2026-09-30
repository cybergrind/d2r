"""Reviewed rare-jewel affix arithmetic for Holy Bolt's recovery/resistance payload.

Unknown modifier families fail closed; adding another family requires its native
property semantics to be reviewed rather than treating planner totals as proof.
"""

from collections import defaultdict


PROPERTIES = {
    'balance1': ('item_fastergethitrate',),
    'res-all': ('fireresist', 'lightresist', 'coldresist', 'poisonresist'),
    'res-fire': ('fireresist',),
    'dmg-to-mana': ('item_damagetomana',),
}


def reviewed_bounds(jewel, tables):
    if jewel.get('base') != 'jew' or jewel.get('quality') != 4:
        raise ValueError('Expected an ordinary rare jewel')
    mods = jewel.get('mods')
    if not isinstance(mods, dict) or not mods:
        raise ValueError('Missing reviewed jewel affixes')
    bounds = defaultdict(lambda: [0, 0])
    actual = defaultdict(int)
    groups = set()
    for key, rolls in mods.items():
        if not isinstance(key, str) or key[:2] not in ('mp', 'ms') or not key[2:].isdecimal():
            raise ValueError('Unsupported jewel affix identity')
        row = tables.get(key[:2], {}).get(key[2:])
        if not row or row.get('rare') != 1 or row.get('itype1') != 'jewl' or row.get('mod2code'):
            raise ValueError('Unsupported native jewel affix')
        group = (key[:2], row.get('group'))
        if group in groups:
            raise ValueError('Conflicting jewel affix groups')
        groups.add(group)
        properties = PROPERTIES.get(row.get('mod1code'))
        low, high = row.get('mod1min'), row.get('mod1max')
        if (
            not properties
            or type(low) is not int
            or type(high) is not int
            or low > high
            or not isinstance(rolls, list)
            or len(rolls) != 1
            or type(rolls[0]) is not int
            or not low <= rolls[0] <= high
        ):
            raise ValueError('Unreviewed or out-of-range jewel affix roll')
        for name in properties:
            bounds[name][0] += low
            bounds[name][1] += high
            actual[name] += rolls[0]
    if dict(actual) != jewel.get('stats'):
        raise ValueError('Planner jewel totals do not match its native affixes')
    return {name: tuple(values) for name, values in bounds.items()}
