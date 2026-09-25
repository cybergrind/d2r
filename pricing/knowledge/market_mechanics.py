"""Reviewed impossible-variant facts for verified catalog identities."""

from pricing.knowledge.definition_store import catalog
from pricing.knowledge.market_base_catalog import equipment_base
from pricing.knowledge.market_named_bases import resolve_equipment_base
from pricing.knowledge.market_named_sockets import fixed_native_socket_count, single_socket_payload
from pricing.knowledge.named_ethereal import intrinsic_ethereal


# Verified pricing/raw/d2data/misc.json (nodurability=1) and itemtypes.json
# (MaxSockets1/2/3=0), 2026-09-24. Do not generalize from nodurability alone:
# indestructible weapons have separate ethereal rules.
# Pinned itemtypes.json explicitly has MaxSockets1/2/3=0 for all four.
# Weapon base rows omit gemsockets; omission alone is never the proof.
THROWING_TYPES = frozenset({'jave', 'ajav', 'tkni', 'taxe'})


def is_nondurable_bow(item_type, no_durability):
    # Never generalize to Phase Blades: upgraded ethereal items are distinct.
    return item_type in ('bow', 'abow', 'xbow') and type(no_durability) is int and no_durability == 1


def apply_bow_ethereal(row, source):
    apply_expected(
        row,
        [('ethereal', '738', False)],
        {
            **source,
            'kind': 'bow_ethereal_mechanics',
            'reference': 'third-parties/D2MOO/source/D2Game/src/ITEMS/Items.cpp:ITEMS_MakeEthereal',
            'durability_reference': 'third-parties/D2MOO/source/D2Common/src/Items/Items.cpp:ITEMS_HasDurability',
        },
        'nondurable bow family mechanics',
    )


def is_nondurable_sword(item_type, no_durability):
    return item_type == 'swor' and type(no_durability) is int and no_durability == 1


def apply_ordinary_sword_ethereal(row, source):
    apply_expected(
        row,
        [('ethereal', '738', False)],
        {
            **source,
            'kind': 'ordinary_nondurable_sword_mechanics',
            'reference': 'third-parties/D2MOO/source/D2Game/src/ITEMS/Items.cpp:ITEMS_MakeEthereal',
            'upgrade_reference': 'third-parties/d2data/json/cubemain.json:129-136,151-154',
        },
        'ordinary nondurable sword quality mechanics',
    )


def cannot_socket(item_type, capacity):
    if item_type in THROWING_TYPES:
        return capacity is None or (type(capacity) is int and capacity == 0)
    return item_type in ('glov', 'boot', 'belt') and type(capacity) is int and capacity == 0


CATALOGS = {
    ('Ring', 'misc'),
    ('Amulet', 'misc'),
    ('Small Charm', 'charms'),
    ('Large Charm', 'charms'),
    ('Grand Charm', 'charms'),
    ('Crafted Sunder Charm', 'charms'),
    ('Jewel', 'jewels'),
    ('Colossal Jewel', 'jewels'),
}
SOURCE = {
    'kind': 'base_mechanics',
    'paths': ['pricing/raw/d2data/misc.json', 'pricing/raw/d2data/itemtypes.json'],
    'reviewed_at': '2026-09-24',
}


def conflict(row, message):
    conflicts = row.setdefault('mechanics_conflicts', [])
    if message not in conflicts:
        conflicts.append(message)


def named_base(row):
    quality = {'unique': 'unique', 'uniques': 'unique', 'set': 'set', 'sets': 'set'}.get(row.get('category'))
    if quality is None:
        return False
    try:
        definitions = catalog()
    except OSError, ValueError, KeyError, TypeError:
        return False
    variants = definitions.named_variants.get((quality, row.get('name')), ())
    allowed = {name for name, _ in CATALOGS}
    codes = set()
    for definition in variants:
        if definition.get('base_name') not in allowed or len(definition.get('base_codes', ())) != 1:
            return False
        codes.update(definition['base_codes'])
    if len(codes) != 1:
        return False
    code = next(iter(codes))
    if row.get('base_code') not in (None, code):
        conflict(row, 'Catalog identity contradicts supplied base code.')
    else:
        row['base_code'] = code
        row.setdefault('facet_basis', {})['base_code'] = {
            'kind': 'named_definition',
            'path': 'pricing/data/appraisal-definitions.json',
            'generation': definitions.generation,
        }
    return True


def apply_mechanics(row):
    apply_unsocketed_contents(row)
    if row.get('category') == 'crafted':
        from pricing.knowledge.market_crafted import apply_crafted_facts

        apply_crafted_facts(row)
        return
    if row.get('category') == 'base':
        apply_base_equipment_facts(row)
        return
    if (row.get('name'), row.get('category')) not in CATALOGS and not named_base(row):
        resolve_equipment_base(row)
        apply_named_equipment_facts(row)
        return
    properties = row['properties']
    # Native charm types force magic quality and cannot be rare. Named unique
    # charms have separate catalog identities; crafted sunders are not included.
    if row.get('category') == 'charms' and row.get('name') in ('Small Charm', 'Large Charm', 'Grand Charm'):
        supplied = properties.get('797', row.get('rarity'))
        if supplied is not None and supplied != 'magic':
            conflict(row, 'Ordinary charm catalog contradicts supplied rarity.')
        elif '797' in properties and supplied is None:
            conflict(row, 'Ordinary charm rarity is explicitly malformed.')
        elif row.get('rarity') not in (None, 'magic'):
            conflict(row, 'Ordinary charm catalog contradicts normalized rarity.')
        else:
            row['rarity'] = 'magic'
            row.setdefault('facet_basis', {})['rarity'] = {
                **SOURCE,
                'kind': 'ordinary_charm_catalog',
                'catalog_path': 'pricing/data/appraisal-traderie-catalog.json',
            }
    expected = [('sockets', '402', 0), ('ethereal', '738', False), ('socket_contents', '934', 'empty')]
    apply_expected(row, expected, SOURCE, 'non-equipment base mechanics')


def apply_expected(row, expected, source, reason):
    properties = row['properties']
    for field, key, value in expected:
        if key not in properties or (field == 'socket_contents' and properties[key] is None):
            row[field] = value
            row.setdefault('facet_basis', {})[field] = dict(source)
            continue
        observed = properties[key]
        valid = (
            type(observed) in (int, float) and observed == 0
            if field == 'sockets'
            else observed is value
            if field == 'ethereal'
            else observed in ('', [])
        )
        if not valid:
            conflict(row, f'{field} contradicts {reason}.')


def apply_named_equipment_facts(row):
    quality = {'unique': 'unique', 'uniques': 'unique', 'set': 'set', 'sets': 'set'}.get(row.get('category'))
    if quality is None:
        return
    try:
        definitions = catalog()
    except OSError, ValueError, KeyError, TypeError:
        return
    variants = definitions.named_variants.get((quality, row.get('name')), ())
    if not variants:
        return
    source = {
        'kind': 'named_equipment_mechanics',
        'path': 'pricing/data/appraisal-definitions.json',
        'generation': definitions.generation,
        'reviewed_at': '2026-09-24',
    }
    fixed = fixed_native_socket_count(variants)
    if fixed is not None:
        if '402' not in row['properties']:
            row['sockets'] = fixed
            row.setdefault('facet_basis', {})['sockets'] = {
                **source,
                'kind': 'fixed_native_sockets',
                'reference': 'third-parties/D2MOO/source/D2Common/src/Items/ItemMods.cpp:ITEMMODS_PropertyFunc14',
            }
        elif type(row['properties']['402']) not in (int, float) or row['properties']['402'] != fixed:
            conflict(row, 'Explicit socket count contradicts fixed native named sockets.')
    proof = single_socket_payload(row, variants)
    if proof:
        properties = row['properties']
        if '402' not in properties:
            row['sockets'] = 1
            row['socket_contents'] = 'filled'
            basis = row.setdefault('facet_basis', {})
            basis['sockets'] = {**source, **proof}
            basis['socket_contents'] = {**source, **proof}
        elif type(properties['402']) not in (int, float) or properties['402'] != 1:
            conflict(row, 'Explicit socket count contradicts named single-filler mechanics.')
    if quality == 'set':
        apply_expected(
            row,
            [('ethereal', '738', False)],
            {
                **source,
                'kind': 'set_quality_mechanics',
                'reference': 'third-parties/D2MOO/source/D2Game/src/ITEMS/Items.cpp:ITEMS_MakeEthereal',
            },
            'set quality mechanics',
        )
    if quality == 'unique' and (ethereal := intrinsic_ethereal(variants)) is not None:
        apply_expected(
            row,
            [('ethereal', '738', ethereal)],
            {
                **source,
                'kind': 'unique_ethereal_mechanics',
                'references': [
                    'third-parties/D2MOO/source/D2Game/src/ITEMS/ItemMode.cpp:sub_6FC4C5F0_End',
                    'third-parties/D2MOO/source/D2Game/src/ITEMS/Items.cpp:ITEMS_MakeEthereal',
                    'third-parties/D2MOO/source/D2Common/src/Items/Items.cpp:ITEMS_HasDurability',
                ],
            },
            'intrinsic unique ethereal/indestructible properties',
        )
    if quality == 'unique' and all(
        is_nondurable_bow(
            variant.get('base_definition', {}).get('type'),
            variant.get('base_definition', {}).get('nodurability'),
        )
        and 'ethereal' not in variant.get('game_definition', {}).values()
        for variant in variants
    ):
        apply_bow_ethereal(row, source)
    # Require a proven nonsocketable family for every same-name definition.
    if all(
        cannot_socket(
            variant.get('base_definition', {}).get('type'), variant.get('base_definition', {}).get('gemsockets')
        )
        for variant in variants
    ):
        apply_expected(
            row,
            [('sockets', '402', 0), ('socket_contents', '934', 'empty')],
            {**source, 'socket_type_reference': 'pricing/raw/d2data/itemtypes.json'},
            'nonsocketable equipment mechanics',
        )


def apply_base_equipment_facts(row):
    resolved = equipment_base(row.get('name'))
    if resolved is None:
        return
    base, source = resolved
    if row.get('base_code') not in (None, base['base_code']):
        conflict(row, 'Listing base code contradicts equipment catalog identity.')
        return
    row['base_code'] = base['base_code']
    row.setdefault('facet_basis', {})['base_code'] = dict(source)
    details = base.get('details', {})
    if is_nondurable_bow(details.get('item_type'), details.get('no_durability')):
        apply_bow_ethereal(row, source)
    if row.get('rarity') in ('normal', 'superior', 'low quality', 'low_quality') and is_nondurable_sword(
        details.get('item_type'), details.get('no_durability')
    ):
        apply_ordinary_sword_ethereal(row, source)
    if cannot_socket(details.get('item_type'), details.get('max_sockets')):
        apply_expected(
            row,
            [('sockets', '402', 0), ('socket_contents', '934', 'empty')],
            {**source, 'socket_type_reference': 'pricing/raw/d2data/itemtypes.json'},
            'nonsocketable equipment mechanics',
        )


def apply_unsocketed_contents(row):
    """An explicit zero capacity cannot contain an inserted rune/gem/jewel."""
    properties = row['properties']
    count = properties.get('402')
    if type(count) not in (int, float) or count != 0:
        return
    contents = properties.get('934')
    if contents is None:
        row['socket_contents'] = 'empty'
        row.setdefault('facet_basis', {})['socket_contents'] = {
            'kind': 'explicit_socket_count',
            'property': '402',
            'value': count,
        }
    elif contents not in ('', []):
        conflict(row, 'Socket contents contradict the explicit zero socket count.')
