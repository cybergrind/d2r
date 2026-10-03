"""Catalog-bound Wisp legacy absorb field; never a general flat/percent alias."""

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.definition_store import catalog


IDENTITY = ('unique', 'Wisp Projector')
CATALOG_ID = '3269425307'
LEGACY = '689'
PERCENT = '1866'


def native_definition(definition=None):
    definition = catalog().named.get(IDENTITY) if definition is None else definition
    if not definition:
        raise ValueError('Missing native Wisp definition.')
    game = definition['game_definition']
    expected = (
        ('abs-ltng%', None, 10, 20),
        ('hit-skill', 'Lightning', 10, 16),
        ('mag%', None, 10, 20),
        ('charged', 'Oak Sage', 15, 2),
        ('charged', 'Heart of Wolverine', 13, 5),
        ('charged', 'Spirit of Barbs', 11, 7),
    )
    actual = tuple(
        (game.get(f'prop{i}'), game.get(f'par{i}'), game.get(f'min{i}'), game.get(f'max{i}')) for i in range(1, 7)
    )
    rolls = definition['roll_ranges']
    if (
        (definition.get('rarity'), definition.get('name')) != IDENTITY
        or definition.get('table_id') != 319
        or tuple(definition.get('base_codes', ())) != ('rin',)
        or game.get('code') != 'rin'
        or actual != expected
        or any(game.get(f'prop{i}') for i in range(7, 13))
        or set(rolls) != {'144', '80'}
        or any(
            (rolls[k]['min'], rolls[k]['max'], rolls[k]['property']) != (10, 20, prop)
            for k, prop in [('144', 'abs-ltng%'), ('80', 'mag%')]
        )
        or definition.get('native_socket_range')
        or definition.get('property_groups')
    ):
        raise ValueError('Changed native Wisp definition.')
    stat = metadata()['stats']['144']
    if (stat['name'], stat['property_id'], stat['shift'], stat['op']) != ('item_absorblight_percent', PERCENT, 0, 0):
        raise ValueError('Changed native Wisp absorb semantics.')
    return definition


def listing_absorb(contract, row, properties, *, definition=None):
    if contract.get('policy') != 'named' or (contract.get('rarity'), contract.get('name')) != IDENTITY:
        return properties
    if LEGACY not in properties:
        return properties
    native_definition(definition)
    if (
        (row.get('rarity'), row.get('name')) != IDENTITY
        or row.get('catalog_id') != CATALOG_ID
        or row.get('base_code') != 'rin'
        or row.get('ethereal') is not False
        or type(row.get('sockets')) is not int
        or row['sockets'] != 0
        or row.get('socket_contents') != 'empty'
    ):
        raise ValueError('Unverified Wisp legacy absorb identity or variant.')
    if PERCENT in properties:
        raise ValueError('Ambiguous Wisp absorb representations.')
    value = properties[LEGACY]
    if type(value) is not int or not 10 <= value <= 20:
        raise ValueError('Wisp lightning absorb must be an integer percentage from 10 to 20.')
    result = dict(properties)
    del result[LEGACY]
    result[PERCENT] = value
    return result
