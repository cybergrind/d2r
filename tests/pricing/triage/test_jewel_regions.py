"""Every jewel region the 2026-10-22 audit priced, through the real engine and the built tables.

The player, 2026-10-22: "we must not have `check` for jewels … not sell by mistake". The regions are the six
verifier tables in rca/2026-10-22/jewel-verify-G1..G6.md; where two tables disagree, the keep side won (main
session ruling). KEEP means the loop stashes the jewel (sell / slow / self); VENDOR means it is sold to an NPC.
"""

import pytest

from pricing.triage.adapters import expanded_properties
from pricing.triage.engine import assess
from pricing.triage.facet_identity import variants
from pricing.triage.family_bands import pattern_bucket
from pricing.triage.runtime import TABLES


KEEP, VENDOR = 'keep', 'vendor'
STASHED = frozenset({'sell', 'slow', 'self', 'keep'})


def allres(value):
    return {'441': value}


def jewel(rarity, properties, level=None):
    properties = expanded_properties(properties | ({'796': level} if level is not None else {}))
    return {
        'category': rarity,
        'name': 'Jewel',
        'family': 'jewl',
        'properties': properties,
        'native_rolls': {},
        'charm_suffix': None,
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'base_name': 'Jewel',
        'base_code': 'jew',
        'identified': True,
        'item_level': 85,
        'rarity': rarity,
        'quantity': 1,
    }


def unique(name, family, code, properties, native_rolls=None, table=None):
    return {
        'category': 'uniques',
        'name': name,
        'family': family,
        'properties': properties,
        'native_rolls': native_rolls or {},
        'charm_suffix': None,
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'base_name': 'Colossal Jewel' if code == 'cjw' else 'Jewel',
        'base_code': code,
        'identified': True,
        'item_level': 110,
        'rarity': 'unique',
        'quantity': 1,
        **({'facet_table_id': table} if table is not None else {}),
    }


MAGIC = [
    # G1 flat damage (magic)
    ('G1 max 5 alone', {'448': 5}, 9, VENDOR),
    ('G1 max 9 alone', {'448': 9}, 27, VENDOR),
    ('G1 Carnage 10 max level 18', {'448': 10}, 18, KEEP),
    ('G1 Carnage 15 max level 18', {'448': 15}, 18, KEEP),
    ('G1 Carbuncle of Wrath 11 max level 9', {'448': 11}, 9, KEEP),
    ('G1 14 max level 56 (P8)', {'448': 14}, 56, KEEP),
    ('G1 Vermilion of Knowledge 13 max + 7 energy', {'448': 13, '421': 7}, 50, KEEP),
    ('G1 Carbuncle of Carnage 18 max', {'448': 18}, 18, KEEP),
    ('G1 Carmine of Carnage 24 max', {'448': 24}, 27, KEEP),
    ('G1 Vermilion of Carnage 27 max', {'448': 27}, 50, KEEP),
    ('G1 Cinnabar of Ire 7 ED + 3 max', {'510': 7, '448': 3}, 9, VENDOR),
    ('G1 Rusty of Wrath 15 ED + 8 max', {'510': 15, '448': 8}, 9, VENDOR),
    ('G1 Realgar of Wrath 25 ED + 8 max', {'510': 25, '448': 8}, 37, VENDOR),
    ('G1 Rusty of Carnage 19 ED + 15 max', {'510': 19, '448': 15}, 18, KEEP),
    ('G1 Ruby of Carnage 38 ED + 13 max', {'510': 38, '448': 13}, 58, KEEP),
    ('G1 min 8 alone', {'416': 8}, 30, VENDOR),
    ('G1 Crimson of Bliss 14 min', {'416': 14}, 37, VENDOR),
    ('G1 Scarlet of Ire 4 min + 5 max', {'416': 4, '448': 5}, 6, VENDOR),
    ('G1 Ruby of Bliss 35 ED + 7 min', {'510': 35, '416': 7}, 58, KEEP),
    ('G1 Realgar of Bliss 25 ED + 8 min', {'510': 25, '416': 8}, 37, VENDOR),
    ('G1 Shimmering of Carnage 7 @ + 13 max', {**allres(7), '448': 13}, 18, KEEP),
    ('G1 Shimmering of Wrath 7 @ + 8 max', {**allres(7), '448': 8}, 12, VENDOR),
    ('G1 Scarlet of Fervor 15 IAS + 4 min', {'457': 15, '416': 4}, 31, KEEP),
    ('G1 Vermilion of Fervor 15 IAS + 15 max', {'457': 15, '448': 15}, 50, KEEP),
    # G2 IAS (Fervor) with every prefix family
    ('G2 R1 Jewel of Fervor', {'457': 15}, 31, KEEP),
    ('G2 R2 + 30 defense', {'457': 15, '399': 30}, 31, KEEP),
    ('G2 R2 + 9 max', {'457': 15, '448': 9}, 31, KEEP),
    ('G2 R2 + 8 ED', {'457': 15, '510': 8}, 31, KEEP),
    ('G2 R2 + 40 AR', {'457': 15, '423': 40}, 31, KEEP),
    ('G2 R2 + 10 fire res', {'457': 15, '427': 10}, 31, KEEP),
    ('G2 R2 + 18 lightning res', {'457': 15, '428': 18}, 31, KEEP),
    ('G2 R2 + 15 mana', {'457': 15, '400': 15}, 31, KEEP),
    ('G2 R2 + 5 MF', {'457': 15, '461': 5}, 31, KEEP),
    ('G2 R3a Rusty 15 ED', {'457': 15, '510': 15}, 31, KEEP),
    ('G2 R3b Realgar 25 ED', {'457': 15, '510': 25}, 37, KEEP),
    ('G2 R3c Ruby 35 ED', {'457': 15, '510': 35}, 58, KEEP),
    ('G2 R4a Shimmering 6 @', {'457': 15, **allres(6)}, 31, KEEP),
    ('G2 R4b Shimmering 9 @', {'457': 15, **allres(9)}, 31, KEEP),
    ('G2 R4c Scintillating 13 @', {'457': 15, **allres(13)}, 31, KEEP),
    ('G2 R5 fire 25', {'457': 15, '427': 25}, 31, KEEP),
    ('G2 R5 lightning 25', {'457': 15, '428': 25}, 31, KEEP),
    ('G2 R5 cold 25', {'457': 15, '426': 25}, 31, KEEP),
    ('G2 R5 poison 25', {'457': 15, '401': 25}, 31, KEEP),
    ('G2 R6 Argent 90 AR', {'457': 15, '423': 90}, 31, KEEP),
    ('G2 R7 Vermillion 13 max', {'457': 15, '448': 13}, 50, KEEP),
    # G3 ED alone and Ruby pairs
    ('G3 E1 15 ED', {'510': 15}, 9, VENDOR),
    ('G3 E1 20 ED', {'510': 20}, 9, VENDOR),
    ('G3 E2 25 ED', {'510': 25}, 37, VENDOR),
    ('G3 E2 30 ED', {'510': 30}, 37, VENDOR),
    ('G3 E3 33 ED', {'510': 33}, 58, VENDOR),
    ('G3 E4 35 ED', {'510': 35}, 58, KEEP),
    ('G3 E4 40 ED', {'510': 40}, 58, KEEP),
    ('G3 R1 31 ED + 9 str', {'510': 31, '437': 9}, 58, KEEP),
    ('G3 R2 35 ED + 7 dex', {'510': 35, '429': 7}, 58, KEEP),
    ('G3 R3 34 ED + 20 life', {'510': 34, '418': 20}, 58, KEEP),
    ('G3 R4 32 ED + 12 life', {'510': 32, '418': 12}, 58, KEEP),
    ('G3 R5 31 ED + -15% req', {'510': 31, '420': -15}, 58, KEEP),
    ('G3 R5b 25 ED + -15% req', {'510': 25, '420': -15}, 37, KEEP),
    ('G3 24 ED + -15% req', {'510': 24, '420': -15}, 37, VENDOR),
    ('G3 R6 36 ED + 7 FHR', {'510': 36, '430': 7}, 58, KEEP),
    ('G3 R6b 30 ED + 7 FHR', {'510': 30, '430': 7}, 44, KEEP),
    ('G3 29 ED + 7 FHR', {'510': 29, '430': 7}, 44, VENDOR),
    ('G3 R6b 30 ED + 5 str', {'510': 30, '437': 5}, 42, KEEP),
    ('G3 29 ED + 9 str', {'510': 29, '437': 9}, 42, VENDOR),
    ('G3 R7 34 ED + 7 MF', {'510': 34, '461': 7}, 58, KEEP),
    ('G3 R8 33 ED + 5 energy', {'510': 33, '421': 5}, 58, VENDOR),
    ('G3 R8 37 ED + 5 energy', {'510': 37, '421': 5}, 58, KEEP),
    ('G3 Realgar of Hope 25 ED + 15 life', {'510': 25, '418': 15}, 37, KEEP),
    ('G3 Realgar 25 ED + 14 life', {'510': 25, '418': 14}, 37, VENDOR),
    ('G3 Realgar 25 ED + 9 str', {'510': 25, '437': 9}, 42, VENDOR),
    ('G3 Rusty 14 ED + 6 dex', {'510': 14, '429': 6}, 9, VENDOR),
    ('G3 Realgar 26 ED + 1 energy', {'510': 26, '421': 1}, 37, VENDOR),
    # G3 all resistances
    ('G3 A1 6 @', allres(6), 12, VENDOR),
    ('G3 A2 9 @', allres(9), 12, VENDOR),
    ('G3 A3 10 @', allres(10), 12, VENDOR),
    ('G3 A4 11 @', allres(11), 26, KEEP),
    ('G3 A4 15 @', allres(15), 26, KEEP),
    ('G3 A5 15 @ + 20 life', {**allres(15), '418': 20}, 37, KEEP),
    ('G3 A6 13 @ + 10 life', {**allres(13), '418': 10}, 37, KEEP),
    ('G3 A7 15 @ + 7 str', {**allres(15), '437': 7}, 42, KEEP),
    ('G3 A8 12 @ + 8 dex', {**allres(12), '429': 8}, 28, KEEP),
    ('G3 A9 12 @ + 8 energy', {**allres(12), '421': 8}, 26, KEEP),
    ('G3 A10 15 @ + -15% req', {**allres(15), '420': -15}, 26, KEEP),
    ('G3 A11 15 @ + 7 FHR', {**allres(15), '430': 7}, 36, KEEP),
    ('G3 A12 13 @ + 8 MF', {**allres(13), '461': 8}, 26, KEEP),
    ('G3 A13 10 @ + 6 str', {**allres(10), '437': 6}, 42, KEEP),
    ('G3 A13 8 @ + 5 dex', {**allres(8), '429': 5}, 28, KEEP),
    ('G3 7 @ + 9 str', {**allres(7), '437': 9}, 42, VENDOR),
    ('G3 10 @ + 4 str', {**allres(10), '437': 4}, 12, VENDOR),
    ('G3 A14 5 @ + 9 life', {**allres(5), '418': 9}, 37, KEEP),
    ('G3 6 @ + 8 life', {**allres(6), '418': 8}, 12, VENDOR),
    ('G3 A15 10 @ + 7 FHR', {**allres(10), '430': 7}, 36, VENDOR),
    ('G3 A15 9 @ + -15% req', {**allres(9), '420': -15}, 12, VENDOR),
    ('G3 A15 8 @ + 9 energy', {**allres(8), '421': 9}, 12, VENDOR),
    ('G3 A15 10 @ + 9 MF', {**allres(10), '461': 9}, 19, VENDOR),
    # G3 one resistance (S1/S2); FHR and life pairs follow G6 where it keeps
    ('G3 S1 30 fire res', {'427': 30}, 30, VENDOR),
    ('G3 S1 12 lightning res', {'428': 12}, 9, VENDOR),
    ('G3 S2 30 fire res + 6 str', {'427': 30, '437': 6}, 30, VENDOR),
    ('G3 S2 / G6 2 30 lightning res + 7 FHR', {'428': 30, '430': 7}, 36, KEEP),
    ('G3 S2 / G6 4 25 cold res + 20 life', {'426': 25, '418': 20}, 37, KEEP),
    # G6 singles
    ('G6 1 7 FHR alone', {'430': 7}, 36, VENDOR),
    ('G6 1 7 FHR + 20 defense', {'430': 7, '399': 20}, 36, VENDOR),
    ('G6 1 7 FHR + 10 mana', {'430': 7, '400': 10}, 36, VENDOR),
    ('G6 2 7 FHR + 16 mana', {'430': 7, '400': 16}, 36, KEEP),
    ('G6 2 7 FHR + 25 fire res', {'430': 7, '427': 25}, 36, KEEP),
    ('G6 2 7 FHR + 70 AR', {'430': 7, '423': 70}, 36, KEEP),
    ('G6 2 7 FHR + 45 defense', {'430': 7, '399': 45}, 36, KEEP),
    ('G6 2 7 FHR + 5 MF', {'430': 7, '461': 5}, 36, KEEP),
    ('G6 3 12 life + 20 cold res', {'418': 12, '426': 20}, 37, VENDOR),
    ('G6 3 8 life alone', {'418': 8}, 9, VENDOR),
    ('G6 4 15 life alone', {'418': 15}, 37, KEEP),
    ('G6 4 18 life + 18 mana', {'418': 18, '400': 18}, 37, KEEP),
    ('G6 4 16 life + 70 AR', {'418': 16, '423': 70}, 37, KEEP),
    ('G6 4 15 life + 30 defense', {'418': 15, '399': 30}, 37, KEEP),
    ('G6 5 15 mana + 9 str', {'400': 15, '437': 9}, 42, VENDOR),
    ('G6 5 20 mana alone', {'400': 20}, 30, VENDOR),
    ('G6 6 9 str alone', {'437': 9}, 42, VENDOR),
    ('G6 6 9 dex + 30 AR', {'429': 9, '423': 30}, 28, VENDOR),
    ('G6 7 25 fire res + 8 MF', {'427': 25, '461': 8}, 30, VENDOR),
    ('G6 8 -15% req + 30 defense', {'420': -15, '399': 30}, 9, VENDOR),
    ('G6 8 -15% req + 18 mana', {'420': -15, '400': 18}, 30, VENDOR),
    ('G6 8 -15% req alone', {'420': -15}, 1, VENDOR),
    ('G6 9 15 MF', {'461': 15}, 19, VENDOR),
    ('G6 9 7 MF + 20 gold', {'461': 7, '460': 20}, 19, VENDOR),
    ('G6 10 30 gold', {'460': 30}, 1, VENDOR),
    ('G6 11 100 AR + 10 MF', {'423': 100, '461': 10}, 19, VENDOR),
    ('G6 12 Thunder 1-100 lightning damage', {'478': 1, '479': 100}, 27, VENDOR),
    ('G6 13 Burning 25-50 fire damage', {'458': 25, '459': 50}, 27, VENDOR),
    ('G6 14 Glacier 5-15 cold damage', {'482': 5, '483': 15}, 27, VENDOR),
    ('G6 15 Envy poison', {'589': 20}, 27, VENDOR),
    ('G6 16 50 defense + 3 thorns', {'399': 50, '415': 3}, 27, VENDOR),
    ('G6 16 15 ED + 1 light radius', {'510': 15, '422': 1}, 9, VENDOR),
]

RARE = [
    # G1 rare flat damage (keep side of G1 vs G4)
    ('G1 rare 9 max alone', {'448': 9}, 27, VENDOR),
    ('G1 P6 rare 10 max', {'448': 10}, 27, KEEP),
    ('G1 P6 / G4 L rare 14 max level 9', {'448': 14}, 9, KEEP),
    ('G1 P7 rare 8 max + 8 min', {'448': 8, '416': 8}, 30, KEEP),
    ('G1 rare 8 min alone', {'416': 8}, 30, VENDOR),
    ('G4 B rare 30 ED + 1 max + 43 AR', {'510': 30, '448': 1, '423': 43}, 37, VENDOR),
    # G4 A: three good rolls
    ('G4 A 9 str + 9 dex + 7 FHR', {'437': 9, '429': 9, '430': 7}, 44, KEEP),
    ('G4 A 25 ED + 50 AR + 25 fire res', {'510': 25, '423': 50, '427': 25}, 37, KEEP),
    # G4 P / V: named pairs
    ('G4 P 30 ED + 10 @', {'510': 30, **allres(10)}, 37, KEEP),
    ('G4 P 30 ED + 9 max', {'510': 30, '448': 9}, 37, KEEP),
    ('G4 P 10 @ + 8 max', {**allres(10), '448': 8}, 27, KEEP),
    ('G4 P 22 ED + 9 min', {'510': 22, '416': 9}, 37, KEEP),
    ('G4 P 10 @ + 30 fire res total', {**allres(10), '427': 30}, 30, KEEP),
    ('G4 V 25 ED + -15% req', {'510': 25, '420': -15}, 37, KEEP),
    ('G4 V 30 ED + 7 FHR', {'510': 30, '430': 7}, 44, KEEP),
    ('G4 V 30 ED + 5 str', {'510': 30, '437': 5}, 42, KEEP),
    ('G4 V 30 ED + 7 dex', {'510': 30, '429': 7}, 37, KEEP),
    # main session: the rare Shimmering of Virility / Daring twin sells
    ('G3 A13 / G4 B rare 10 @ + 6 str', {**allres(10), '437': 6}, 42, KEEP),
    ('G3 A13 / G4 B rare 8 @ + 5 dex', {**allres(8), '429': 5}, 28, KEEP),
    # G4 B: other pairs
    ('G4 B 19 ED + 8 @', {'510': 19, **allres(8)}, 37, VENDOR),
    ('G4 B 30 ED + 43 AR', {'510': 30, '423': 43}, 37, VENDOR),
    ('G4 B 22 ED + -15% req', {'510': 22, '420': -15}, 37, VENDOR),
    ('G4 B 29 ED + 7 FHR', {'510': 29, '430': 7}, 44, VENDOR),
    ('G4 B 7 FHR + 30 fire res', {'430': 7, '427': 30}, 44, VENDOR),
    ('G4 B 9 str + 9 dex', {'437': 9, '429': 9}, 42, VENDOR),
    ('G4 B 8 min + 8 dex', {'416': 8, '429': 8}, 30, VENDOR),
    ('G4 B 55 AR + 7 FHR', {'423': 55, '430': 7}, 44, VENDOR),
    ('G4 B 7 FHR + 8 max', {'430': 7, '448': 8}, 44, VENDOR),
    ('G4 B 7 FHR + 24 poison res', {'430': 7, '401': 24}, 44, VENDOR),
    ('G4 B 9 dex + 30 fire res', {'429': 9, '427': 30}, 30, VENDOR),
    # G4 C: one good roll; D: none
    ('G4 C 30 ED alone', {'510': 30}, 37, VENDOR),
    ('G4 C 10 @ alone', allres(10), 12, VENDOR),
    ('G4 C 30 fire res alone', {'427': 30}, 30, VENDOR),
    ('G4 C 7 FHR alone', {'430': 7}, 44, VENDOR),
    ('G4 C -15% req alone', {'420': -15}, 1, VENDOR),
    ('G4 C 9 str alone', {'437': 9}, 42, VENDOR),
    ('G4 D 10 MF + 15 mana + 30 defense', {'461': 10, '400': 15, '399': 30}, 30, VENDOR),
    ('G4 D 8 life + 20 gold + 3 thorns', {'418': 8, '460': 20, '415': 3}, 30, VENDOR),
]

COLOSSAL = {
    "Defender's Fire": ('735', '750'),
    "Defender's Bile": ('723', '783'),
    "Protector's Frost": ('609', '747'),
    "Guardian's Thunder": ('736', '743'),
    "Guardian's Light": ('1877', '1879'),
    "Protector's Stone": ('1881', None),
}
FACET_ROLLS = [(3, 3), (3, 4), (4, 3), (4, 4), (5, 3), (3, 5), (5, 4), (4, 5), (5, 5)]


def cases():
    for rarity, rows in (('magic', MAGIC), ('rare', RARE)):
        for label, properties, level, expected in rows:
            yield pytest.param(jewel(rarity, properties, level), expected, id=f'{rarity} {label}')
    for table, (mastery, pierce), trigger, _ in variants():
        for skill, res in FACET_ROLLS:
            item = unique('Rainbow Facet', 'jewl', 'jew', {mastery: skill, pierce: res}, {trigger: 100}, table)
            yield pytest.param(item, KEEP, id=f'G5 Rainbow Facet {table} {skill}/{res}')
        # An undecoded trigger prices from the pooled roll region, never CHECK.
        item = unique('Rainbow Facet', 'jewl', 'jew', {mastery: 5, pierce: 5})
        yield pytest.param(item, KEEP, id=f'G5 Rainbow Facet {table} 5/5 trigger unread')
        item = unique('Rainbow Facet', 'jewl', 'jew', {mastery: 3, pierce: 4})
        yield pytest.param(item, KEEP, id=f'G5 Rainbow Facet {table} 3/4 trigger unread')
    for name, (pierce, mastery) in COLOSSAL.items():
        for res, skill in ((5, 5), (7, 6), (8, 8), (9, 7), (10, 6), (10, 10)):
            properties = {pierce: res, '461': 20, '460': 30, '776': 4} | ({mastery: skill} if mastery else {})
            yield pytest.param(unique(name, 'cjwl', 'cjw', properties), KEEP, id=f'G5 {name} -{res}/{skill}')
        # An unreadable -res roll takes the lowest supported region.
        yield pytest.param(unique(name, 'cjwl', 'cjw', {'461': 20}), KEEP, id=f'G5 {name} roll unread')
    # Protector's Stone's pierce (native 366) has no market projection: the native roll still prices it.
    stone = unique("Protector's Stone", 'cjwl', 'cjw', {'461': 20}, {'366:0': 10})
    yield pytest.param(stone, KEEP, id="G5 Protector's Stone -10 native roll")
    for rarity in ('magic', 'rare'):
        item = jewel(rarity, {'427': 20}) | {'family': 'cjwl', 'base_code': 'cjw', 'base_name': 'Colossal Jewel'}
        yield pytest.param(item, KEEP, id=f'G5 non-unique {rarity} Colossal Jewel')


@pytest.mark.parametrize(('item', 'expected'), list(cases()))
def test_every_jewel_region_has_a_confident_verdict(item, expected):
    result = assess(item, TABLES.load())

    assert result['verdict'] != 'check', result['reason']
    if expected == KEEP:
        assert result['verdict'] in STASHED, result['reason']
    else:
        assert result['verdict'] == 'vendor', result['reason']


def test_the_fervor_floor_band_is_supported():
    tables = TABLES.load()
    floor = next(r for r in tables['rules']['rows'] if r.get('band_role') == 'floor' and r.get('family') == 'jewl')
    band = tables['bands']['family', 'jewl', pattern_bucket(floor)]

    # A thin floor is the one way a 15-IAS jewel could go back to sparse asks (G2 §4.6).
    assert band['sellers'] >= 3
    assert band['q1_ist'] >= tables['rules']['keep_ist']


def jewel_listing(seller, price, properties):
    from tests.pricing.triage.test_bands import listing

    row = listing(seller, price)
    row.update(name='Jewel', category='misc', rarity='magic', sockets=0, socket_contents='empty')
    row['properties'] = row['properties'] | properties
    return row


def test_a_listed_requirements_roll_has_the_drop_sign():
    # Traderie stores "-15% requirements" as 420 = 15; a drop carries -15 (G3 §6.1).
    from pricing.triage.adapters import from_listing

    assert from_listing(jewel_listing(1, 1, {'420': 15}))['properties']['420'] == -15
    assert from_listing(jewel_listing(1, 1, {'420': -15}))['properties']['420'] == -15
    armor = jewel_listing(1, 1, {'420': 15}) | {'name': 'Archon Plate', 'category': 'base'}
    assert from_listing(armor)['properties']['420'] == 15


def test_a_jewel_defense_roll_reaches_the_market_property():
    from pricing.triage.adapters import from_drop
    from tests.pricing.triage.test_flat_damage_projection import carnage_capture, stat

    capture = carnage_capture()
    capture['decoded_stats'].append(stat(31, 45, 'armorclass'))
    assert from_drop(capture)['properties']['399'] == 45


def test_a_thin_compound_band_falls_back_to_the_floor_and_floor_asks_are_residual():
    from pricing.triage.bands import build_bands
    from pricing.triage.engine import prepare_tables

    fervor = {'457': {'min': 15}}
    floor = {
        'family': 'jewl',
        'category': 'magic',
        'properties': fervor,
        'pattern': {'properties': fervor},
        'bucket': 'fervor-floor',
        'band_role': 'floor',
        'premium': True,
    }
    ruby = {'457': {'min': 15}, '510': {'min': 31}}
    compound = {'family': 'jewl', 'category': 'magic', 'properties': ruby, 'pattern': {'properties': ruby}}
    compound |= {'bucket': 'ruby-fervor'}
    rules = [compound, floor]  # file order must not matter: the floor prices last
    rows = [jewel_listing(seller, 1, {'457': 15}) for seller in range(3)]
    rows += [jewel_listing(10 + seller, 40, {'457': 15, '510': 35}) for seller in range(2)]
    data = prepare_tables(build_bands(rows, [], rules=rules), {'keep_ist': 0.25, 'rows': rules}, {'rows': []})
    ruby_jewel = jewel('magic', {'457': 15, '510': 35})

    result = assess(ruby_jewel, data)
    # Two Ruby sellers are too thin: the floor (three plain sellers at 1, no compound asks mixed in) prices it.
    assert result['verdict'] == 'sell'
    assert result['band']['sellers'] == 3
    assert result['decision_ist'] == 1
