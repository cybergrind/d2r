"""Item-specific ethereal proof from explicit total defense, never omitted flags."""

from pricing.knowledge.assessment.handlers.definitions import named_definitions


MODE = 'arachnid_total_defense'
IDENTITY = ('unique', 'Arachnid Mesh')
BASE_CODE = 'ulc'
PROPERTIES = (
    ('ac%', 90, 120, None),
    ('cast2', 20, 20, None),
    ('charged', 11, 3, 'Venom'),
    ('allskills', 1, 1, None),
    ('slow', 10, 10, None),
    ('mana%', 5, 5, None),
)


def native_arachnid(definition=None):
    """Bind the arithmetic to this unsocketable, non-upgradable native item."""
    if definition is None:
        definition = named_definitions().get(IDENTITY)
    if not definition:
        return False
    base, game = definition.get('base_definition', {}), definition.get('game_definition', {})
    if (
        (definition.get('rarity'), definition.get('name')) != IDENTITY
        or definition.get('base_name') != 'Spiderweb Sash'
        or definition.get('base_code') != BASE_CODE
        or list(definition.get('base_codes', ())) != [BASE_CODE]
        or any(
            base.get(k) != v
            for k, v in {
                'code': BASE_CODE,
                'ultracode': BASE_CODE,
                'type': 'belt',
                'minac': 55,
                'maxac': 62,
                'gemsockets': 0,
            }.items()
        )
        or game.get('code') != BASE_CODE
        or any(
            definition.get(k)
            for k in ('property_groups', 'native_socket_range', 'variable_per_level_effects', 'fixed_per_level_effects')
        )
    ):
        return False
    for slot in range(1, 13):
        if slot > len(PROPERTIES):
            if game.get(f'prop{slot}'):
                return False
            continue
        prop, low, high, parameter = PROPERTIES[slot - 1]
        if (game.get(f'prop{slot}'), game.get(f'min{slot}'), game.get(f'max{slot}')) != (prop, low, high):
            return False
        actual = game.get(f'par{slot}')
        if actual != parameter and not (parameter is None and actual in (None, '', 0)):
            return False
    return True


def arachnid_ethereal(row, *, definition=None):
    """Return False only for a proved nonethereal listing; otherwise unknown.

    Native enhanced-defense armor starts from max base defense + 1. Even the
    conservative ethereal minimum (without the max+1 adjustment) is above every
    possible nonethereal total here. No socket or flat-defense contribution can
    obscure that distinction on this specific verified belt. Bonus-defense field
    399 is deliberately never used as total defense (1855).
    An explicit nonethereal flag needs no inference, but a supplied total must
    still be consistent with the native roll.
    """
    props = row.get('properties', {})
    ed, total = props.get('425'), props.get('1855')
    ethereal = row.get('ethereal')
    if (
        (row.get('rarity'), row.get('name')) != IDENTITY
        or row.get('base_code') != BASE_CODE
        or not (row.get('base_upgrade') is None or row['base_upgrade'] is False)
        or not (ethereal is None or ethereal is False)
        or type(row.get('sockets')) is not int
        or row['sockets'] != 0
        or row.get('socket_contents') != 'empty'
        or props.get('930') not in (None, 'Elite')
        or not (props.get('1216') is None or props['1216'] is False)
        or not (props.get('738') is None or props['738'] is False)
        or ('402' in props and (type(props['402']) is not int or props['402'] != 0))
        or type(ed) is not int
        or not 90 <= ed <= 120
        or not native_arachnid(definition)
    ):
        return None
    if ethereal is False and '1855' not in props:
        return False
    if type(total) is not int or total != 63 * (100 + ed) // 100 or total >= (55 * 3 // 2) * (100 + ed) // 100:
        return None
    return False
