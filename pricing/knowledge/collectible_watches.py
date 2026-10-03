"""Reviewed combination demand from cached guides, never a price or sale claim."""

import hashlib
import json


GUIDE = 'pricing/raw/mr/items__valuable-magic-items.html'
PREFIX = 'third-parties/d2data/json/magicprefix.json'
SUFFIX = 'third-parties/d2data/json/magicsuffix.json'
# Native properties and bounds are independently checked against the source tables.
AFFIXES = {
    (PREFIX, '277'): ('lcha', (('mag%', 8, 12),)),
    (PREFIX, '480'): ('lcha', (('skilltab', 1, 1),)),
    (SUFFIX, '280'): ('lcha', (('gold%', 21, 30),)),
    (SUFFIX, '281'): ('lcha', (('gold%', 31, 40),)),
    (SUFFIX, '284'): ('scha', (('gold%', 5, 10),)),
    (PREFIX, '649'): ('scha', (('ltng-min', 1, 1), ('ltng-max', 44, 71))),
    (PREFIX, '661'): ('scha', (('dmg-pois', 299, 299),)),
    (SUFFIX, '693'): ('scha', (('dmg-pois', 86, 86),)),
    (PREFIX, '302'): ('scha', (('mana', 8, 12),)),
    (SUFFIX, '347'): ('scha', (('hp', 5, 10),)),
    (SUFFIX, '348'): ('scha', (('hp', 11, 15),)),
    (SUFFIX, '267'): ('scha', (('balance1', 5, 5),)),
    (SUFFIX, '401'): ('scha', (('move1', 3, 3),)),
    (PREFIX, '183'): ('jewl', (('dmg-max', 1, 5),)),
    (SUFFIX, '222'): ('jewl', (('dmg-max', 11, 15),)),
    (PREFIX, '196'): ('jewl', (('dmg%', 11, 20),)),
    (PREFIX, '197'): ('jewl', (('dmg%', 21, 30),)),
    (PREFIX, '303'): ('scha', (('mana', 13, 17),)),
    (SUFFIX, '371'): ('jewl', (('ease', -15, -15),)),
    (SUFFIX, '351'): ('jewl', (('hp', 9, 20),)),
    (SUFFIX, '669'): ('jewl', (('dex', 4, 6),)),
    (SUFFIX, '670'): ('jewl', (('dex', 7, 9),)),
    (SUFFIX, '671'): ('jewl', (('enr', 4, 6),)),
    (SUFFIX, '672'): ('jewl', (('enr', 7, 9),)),
    (SUFFIX, '673'): ('jewl', (('str', 5, 6),)),
    (SUFFIX, '674'): ('jewl', (('str', 7, 9),)),
    (PREFIX, '348'): ('scha', (('res-cold', 8, 9),)),
    (PREFIX, '349'): ('scha', (('res-cold', 10, 11),)),
    (PREFIX, '368'): ('scha', (('res-fire', 8, 9),)),
    (PREFIX, '369'): ('scha', (('res-fire', 10, 11),)),
    (PREFIX, '387'): ('scha', (('res-ltng', 8, 9),)),
    (PREFIX, '388'): ('scha', (('res-ltng', 10, 11),)),
    (PREFIX, '407'): ('scha', (('res-pois', 8, 9),)),
    (PREFIX, '408'): ('scha', (('res-pois', 10, 11),)),
    (SUFFIX, '291'): ('scha', (('mag%', 6, 7),)),
    (PREFIX, '319'): ('lcha', (('res-all', 13, 15),)),
    (SUFFIX, '334'): ('lcha', (('hp', 16, 20),)),
    (SUFFIX, '335'): ('lcha', (('hp', 21, 25),)),
    (PREFIX, '256'): ('scha', (('att', 10, 20), ('dmg-max', 1, 3))),
    (PREFIX, '253'): ('lcha', (('att', 49, 76), ('dmg-max', 7, 10))),
    (PREFIX, '322'): ('scha', (('res-all', 3, 5),)),
    (PREFIX, '198'): ('jewl', (('dmg%', 31, 40),)),
    (PREFIX, '337'): ('jewl', (('res-all', 11, 15),)),
    (PREFIX, '376'): ('jewl', (('res-fire', 16, 30),)),
    (PREFIX, '255'): ('mcha', (('att', 21, 48), ('dmg-max', 4, 6))),
    (PREFIX, '321'): ('mcha', (('res-all', 6, 8),)),
    (SUFFIX, '349'): ('scha', (('hp', 16, 20),)),
    (SUFFIX, '336'): ('lcha', (('hp', 26, 30),)),
    (SUFFIX, '337'): ('lcha', (('hp', 31, 35),)),
    (SUFFIX, '338'): ('lcha', (('hp', 36, 40),)),
    (SUFFIX, '339'): ('lcha', (('hp', 41, 45),)),
    (SUFFIX, '171'): ('jewl', (('swing1', 15, 15),)),
    (SUFFIX, '343'): ('mcha', (('hp', 16, 20),)),
    (SUFFIX, '344'): ('mcha', (('hp', 21, 25),)),
    (SUFFIX, '345'): ('mcha', (('hp', 26, 30),)),
    (SUFFIX, '346'): ('mcha', (('hp', 31, 35),)),
}
# Guide labels locate evidence, not item-name predicates. Its ED/IAS value bands
# cross native prefix boundaries: 20 is Rusty, 21-30 Realgar, 31-40 Ruby.
REQUIRED_AFFIXES = {
    'shocking-life': {'prefix': ['649'], 'suffix': ['349'], 'auto': []},
    'pestilent-life': {'prefix': ['661'], 'suffix': ['349'], 'auto': []},
    'pestilent-anthrax': {'prefix': ['661'], 'suffix': ['693'], 'auto': []},
    'rusty-carnage': {'prefix': ['196'], 'suffix': ['222'], 'auto': []},
    'carbuncle-carnage': {'prefix': ['183'], 'suffix': ['222'], 'auto': []},
}
RAW_CONDITIONS = {
    'pestilent-life': {'57:0': {'min': 299, 'max': 299}, '58:0': {'min': 299, 'max': 299}},
    'pestilent-anthrax': {'57:0': {'min': 385, 'max': 385}, '58:0': {'min': 385, 'max': 385}},
}
SPECS = (
    (
        'shocking-life',
        'Small Charm',
        'Shocking Small Charm of Vita',
        '16-20 Life',
        {'50:0': (1, 1), '51:0': (44, 71), '7:0': (16, 20)},
        (),
        'Shocking lightning damage + life: maximum damage 44-71, life 16-20',
        'High',
    ),
    (
        'pestilent-life',
        'Small Charm',
        'Pestilent Small Charm of Vita',
        '16-20 Life',
        {'7:0': (16, 20), '59:0': (6, 6)},
        (('57:0', '58:0'),),
        'Pestilent poison + life: 16-20 life',
        'High',
    ),
    (
        'pestilent-anthrax',
        'Small Charm',
        'Pestilent Small Charm of Anthrax',
        '313+ Poison Damage',
        {'59:0': (12, 12)},
        (('57:0', '58:0'),),
        'Pestilent + Anthrax poison combination',
        'High',
    ),
    (
        'shimmering-balance',
        'Small Charm',
        'Shimmering Small Charm of Balance',
        '4-5 All Resistances',
        {**{f'{s}:0': (4, 5) for s in (39, 41, 43, 45)}, '99:0': (5, 5)},
        (('39:0', '41:0', '43:0', '45:0'),),
        'All resistances + hit recovery: 4-5 all res, 5% FHR',
        'High',
    ),
    (
        'shimmering-inertia',
        'Small Charm',
        'Shimmering Small Charm of Inertia',
        '4-5 All Resistances',
        {**{f'{s}:0': (4, 5) for s in (39, 41, 43, 45)}, '96:0': (3, 3)},
        (('39:0', '41:0', '43:0', '45:0'),),
        'All resistances + run/walk: 4-5 all res, 3% FRW',
        'High',
    ),
    (
        'shimmering-sustenance',
        'Small Charm',
        'Shimmering Small Charm of Sustenance',
        '4-5 All Resistances and 10-15 Life',
        {**{f'{s}:0': (4, 5) for s in (39, 41, 43, 45)}, '7:0': (10, 15)},
        (('39:0', '41:0', '43:0', '45:0'),),
        'All resistances + life: 4-5 all res, 10-15 life (valuable low-level combination)',
        'Very High',
    ),
    (
        'fine-sustenance',
        'Small Charm',
        'Fine Small Charm of Sustenance',
        '3 Maximum Damage and 11-15 Life',
        {'22:0': (3, 3), '19:0': (10, 20), '7:0': (11, 15)},
        (),
        'Maximum damage + attack rating + life: 3 damage, 10-20 AR, 11-15 life (valuable low-level combination)',
        'Very High',
    ),
    (
        'fine-low-life',
        'Small Charm',
        'Fine Small Charm of Life',
        '3 Maximum Damage and 5-10 Life',
        {'22:0': (3, 3), '19:0': (10, 20), '7:0': (5, 10)},
        (),
        'Maximum damage + attack rating + life: 3 damage, 10-20 AR, 5-10 life (valuable low-level combination)',
        'High',
    ),
    (
        'snake-sustenance',
        'Small Charm',
        "Snake's Small Charm of Sustenance",
        '11-15 Life and 10-12 Mana',
        {'7:0': (11, 15), '9:0': (10, 12)},
        (),
        'Life + mana: 11-15 life, 10-12 mana (valuable low-level combination)',
        'High',
    ),
    (
        'rusty-carnage',
        'Jewel',
        'Rusty Jewel of Carnage',
        '18-20% Enhanced Damage and 14-15 Maximum Damage',
        {'17:0': (18, 20), '18:0': (18, 20), '22:0': (14, 15)},
        (('17:0', '18:0'),),
        'Level-18 jewel: 18-20% enhanced damage + 14-15 maximum damage',
        'High',
    ),
    (
        'carbuncle-carnage',
        'Jewel',
        'Carbuncle Jewel of Carnage',
        '18-20 Maximum Damage',
        {'22:0': (18, 20)},
        (),
        'Level-18 jewel: 18-20 combined maximum damage',
        'High',
    ),
    (
        'realgar-fervor',
        'Jewel',
        'Realgar Jewel of Fervor',
        '20-29% Enhanced Damage',
        {'17:0': (20, 29), '18:0': (20, 29), '93:0': (15, 15)},
        (('17:0', '18:0'),),
        'Enhanced damage + attack speed: 20-29% ED, 15% IAS',
        'High',
    ),
    (
        'serpent-life',
        'Small Charm',
        "Serpent's Small Charm of Vita",
        '16-20 Life and 13-17 Mana',
        {'7:0': (16, 20), '9:0': (13, 17)},
        (),
        'Life + mana: 16-20 life, 13-17 mana',
        'High',
    ),
    (
        'scintillating-freedom',
        'Jewel',
        'Scintillating Jewel of Freedom',
        '10-15 All Resistances',
        {**{f'{s}:0': (11, 15) for s in (39, 41, 43, 45)}, '91:0': (-15, -15)},
        (('39:0', '41:0', '43:0', '45:0'),),
        'All resistances + reduced requirements: 11-15 all res, -15% requirements',
        'High',
    ),
    (
        'scintillating-hope',
        'Jewel',
        'Scintillating Jewel of Hope',
        '15-20 Life and 12-15 All Resistances',
        {**{f'{s}:0': (12, 15) for s in (39, 41, 43, 45)}, '7:0': (15, 20)},
        (('39:0', '41:0', '43:0', '45:0'),),
        'All resistances + life: 12-15 all res, 15-20 life',
        'High',
    ),
    *(
        (
            f'scintillating-{attribute}',
            'Jewel',
            'Scintillating Jewel of Daring',
            '5-9 of an Attribute and 12-15 All Resistances',
            {**{f'{s}:0': (12, 15) for s in (39, 41, 43, 45)}, f'{stat}:0': (5, 9)},
            (('39:0', '41:0', '43:0', '45:0'),),
            f'All resistances + {attribute}: 12-15 all res, 5-9 {attribute}',
            'High',
        )
        for attribute, stat in (('strength', 0), ('dexterity', 2), ('energy', 1))
    ),
    *(
        (
            f'{element}-good-luck',
            'Small Charm',
            'Resistance Small Charm of Good Luck',
            '8-11 Resistance and 6-7% Magic Find',
            {f'{stat}:0': (8, 11), '80:0': (6, 7)},
            (),
            f'{element.title()} resistance + magic find: 8-11% res, 6-7% MF',
            'High',
        )
        for element, stat in (('fire', 39), ('lightning', 41), ('cold', 43), ('poison', 45))
    ),
    *(
        (
            f'{element}-life',
            'Small Charm',
            'Resistance Small Charm of Vita',
            '8-11 Resistance and 16-20 Life',
            {f'{stat}:0': (8, 11), '7:0': (16, 20)},
            (),
            f'{element.title()} resistance + life: 8-11% res, 16-20 life',
            'High',
        )
        for element, stat in (('fire', 39), ('lightning', 41), ('cold', 43), ('poison', 45))
    ),
    (
        'shimmering-good-luck',
        'Small Charm',
        'Shimmering Small Charm of Good Luck',
        '4-5 All Resistances and 6-7% Magic Find',
        {**{f'{s}:0': (4, 5) for s in (39, 41, 43, 45)}, '80:0': (6, 7)},
        (('39:0', '41:0', '43:0', '45:0'),),
        'All resistances + magic find: 4-5 all res, 6-7% MF',
        'Very High',
    ),
    (
        'fine-good-luck',
        'Small Charm',
        'Fine Small Charm of Good Luck',
        '2-3 Maximum Damage and 6-7% Magic Find',
        {'22:0': (2, 3), '19:0': (10, 20), '80:0': (6, 7)},
        (),
        'Maximum damage + attack rating + magic find: 2-3 damage, 10-20 AR, 6-7% MF',
        'High',
    ),
    (
        'grand-shimmering-life',
        'Grand Charm',
        'Shimmering Grand Charm of Vita',
        '30-45 Life and 13-15 All Resistances',
        {**{f'{s}:0': (13, 15) for s in (39, 41, 43, 45)}, '7:0': (30, 45)},
        (('39:0', '41:0', '43:0', '45:0'),),
        'All resistances + life: 13-15 all res, 30-45 life',
        'Very High',
    ),
    (
        'grand-shimmering-sustenance',
        'Grand Charm',
        'Shimmering Grand Charm of Sustenance',
        '20-29 Life and 13-15 All Resistances',
        {**{f'{s}:0': (13, 15) for s in (39, 41, 43, 45)}, '7:0': (20, 29)},
        (('39:0', '41:0', '43:0', '45:0'),),
        'All resistances + life: 13-15 all res, 20-29 life',
        'High',
    ),
    (
        'sharp-sustenance',
        'Grand Charm',
        'Sharp Grand Charm of Sustenance',
        '8-10 Maximum Damage and 20-29 Life',
        {'22:0': (8, 10), '19:0': (49, 76), '7:0': (20, 29)},
        (),
        'Maximum damage + attack rating + life: 8-10 damage, 49-76 AR, 20-29 life',
        'High',
    ),
    (
        'fine-life',
        'Small Charm',
        'Fine Small Charm of Vita',
        '3 Maximum Damage and 16-20 Life',
        {'22:0': (3, 3), '19:0': (10, 20), '7:0': (16, 20)},
        (),
        'Maximum damage + attack rating + life: 3 damage, 10-20 AR, 16-20 life',
        'Very High',
    ),
    (
        'sharp-life',
        'Grand Charm',
        'Sharp Grand Charm of Vita',
        '8-10 Maximum Damage and 30-45 Life',
        {'22:0': (8, 10), '19:0': (49, 76), '7:0': (30, 45)},
        (),
        'Maximum damage + attack rating + life: 8-10 damage, 49-76 AR, 30-45 life',
        'Very High',
    ),
    (
        'shimmering-life',
        'Small Charm',
        'Shimmering Small Charm of Vita',
        '4-5 All Resistances and 16-20 Life',
        {**{f'{s}:0': (4, 5) for s in (39, 41, 43, 45)}, '7:0': (16, 20)},
        (('39:0', '41:0', '43:0', '45:0'),),
        'All resistances + life: 4-5 all res, 16-20 life',
        'Very High',
    ),
    (
        'ruby-fervor',
        'Jewel',
        'Ruby Jewel of Fervor',
        '30-40% Enhanced Damage',
        {'17:0': (30, 40), '18:0': (30, 40), '93:0': (15, 15)},
        (('17:0', '18:0'),),
        'Enhanced damage + attack speed: 30-40% ED, 15% IAS',
        'Very High',
    ),
    (
        'scintillating-fervor',
        'Jewel',
        'Scintillating Jewel of Fervor',
        '10-15 All Resistances',
        {**{f'{s}:0': (11, 15) for s in (39, 41, 43, 45)}, '93:0': (15, 15)},
        (('39:0', '41:0', '43:0', '45:0'),),
        'All resistances + attack speed: 11-15 all res, 15% IAS',
        'Very High',
    ),
    (
        'ruby-fire-fervor',
        'Jewel',
        'Ruby Jewel of Fervor',
        '20-30 Fire Resistance',
        {'39:0': (20, 30), '93:0': (15, 15)},
        (),
        "Fire resistance + attack speed: 20-30% fire res, 15% IAS (mercenary Andariel's Visage)",
        'High',
    ),
    (
        'large-sharp-life',
        'Large Charm',
        'Sharp Large Charm of Vita',
        '5-6 Maximum Damage and 20-35 Life',
        {'22:0': (5, 6), '19:0': (21, 48), '7:0': (20, 35)},
        (),
        'Maximum damage + attack rating + life: 5-6 damage, 21-48 AR, 20-35 life',
        'High',
    ),
    (
        'large-shimmering-life',
        'Large Charm',
        'Shimmering Large Charm of Vita',
        '20-35 Life and 7-8 All Resistances',
        {**{f'{s}:0': (7, 8) for s in (39, 41, 43, 45)}, '7:0': (20, 35)},
        (('39:0', '41:0', '43:0', '45:0'),),
        'All resistances + life: 7-8 all res, 20-35 life',
        'High',
    ),
)


def resale_group(key, base, bounds, quote=''):
    """Group reviewed combinations without promoting guide demand to liquidity."""
    stats = set(bounds)
    if stats == {'22:0', '19:0', '7:0'}:
        identity, focus = 'physical-charm-life', 'physical_damage'
    elif (
        base in ('Small Charm', 'Large Charm', 'Grand Charm')
        and stats & {'39:0', '41:0', '43:0', '45:0'}
        and '79:0' not in stats
    ):
        identity, focus = 'resistance-charm', 'resistance'
    elif base == 'Jewel':
        identity, focus = 'socket-jewel', 'socket_combination'
    elif base in ('Small Charm', 'Large Charm', 'Grand Charm') and '79:0' in stats:
        identity, focus = 'gold-find-charm', 'gold_find'
    elif stats == {'7:0', '9:0'}:
        identity, focus = 'resource-charm', 'life_mana'
    elif stats == {'22:0', '19:0', '80:0'}:
        identity, focus = 'physical-charm-magic-find', 'physical_damage'
    elif key in ('shocking-life', 'pestilent-life', 'pestilent-anthrax'):
        identity, focus = 'elemental-charm', 'elemental_damage'
    elif key == 'druid-summoning-life-skiller':
        identity, focus = 'skill-charm', 'druid_summoning'
    else:
        return {}
    if key in (
        'fine-low-life',
        'fine-sustenance',
        'shimmering-sustenance',
        'rusty-carnage',
        'carbuncle-carnage',
        'snake-sustenance',
    ):
        focus = 'low_level'
    difficult = 'difficult to trade' in quote.casefold()
    return {
        'resale_group': {
            'id': identity,
            'qualification': 'candidate',
            'buyer_focus': focus,
            'buyer_scope': 'niche' if focus in ('low_level', 'gold_find') or difficult else 'unverified',
            'trade_effort': 'guide_reports_difficult_trade' if difficult else 'unverified',
            'liquidity': 'unverified',
            'basis': 'reviewed_guide_combination',
        }
    }


def build_combinations(read, guide_rows):
    native = {path: json.loads(read(path)) for path in (PREFIX, SUFFIX)}
    if native[PREFIX]['480'].get('mod1param') != 14:
        raise ValueError('Warcries native skill-tab parameter changed')
    for path, key in ((PREFIX, '661'), (SUFFIX, '693')):
        if native[path][key].get('mod1param') != 150:
            raise ValueError(f'Poison affix duration changed: {path}#{key}')
    for path, key, level in ((PREFIX, '183', 9), (PREFIX, '196', 9), (SUFFIX, '222', 18)):
        if native[path][key].get('levelreq') != level:
            raise ValueError(f'Low-level jewel requirement changed: {path}#{key}')
    for (path, key), (kind, effects) in AFFIXES.items():
        row = native[path].get(key, {})
        actual = tuple(
            (row[f'mod{i}code'], row.get(f'mod{i}min'), row.get(f'mod{i}max'))
            for i in range(1, 8)
            if row.get(f'mod{i}code')
        )
        if (
            row.get('itype1') != kind
            or row.get('spawnable') != 1
            or not 1 <= row.get('level', 0) <= 99
            or actual != effects
        ):
            raise ValueError(f'Collectible affix source changed: {path}#{key}')
    digest = hashlib.sha256(read(GUIDE).encode()).hexdigest()
    from pricing.knowledge.gold_find_watches import gold_specs
    from pricing.knowledge.plain_resistance_watches import planner_specs

    plain_specs, planner_sources = planner_specs(read, read(GUIDE))
    gold, gold_sources = gold_specs(read, read(GUIDE))
    planner_sources.update(gold_sources)
    result = []
    for key, base, label, quote, bounds, equal, description, tier in (*SPECS, *gold, *plain_specs):
        matches = [
            (i, r)
            for i, r in enumerate(guide_rows)
            if r[0] == label and quote in r[2] and (key not in planner_sources or r[1] == tier)
        ]
        if len(matches) != 1 or matches[0][1][1] != tier:
            raise ValueError(f'Collectible guide combination changed: {label}')
        index, row = matches[0]
        result.append(
            {
                'name': base,
                'kind': 'affixed_value_watch',
                'rarity': 'magic',
                'date': '2026-10-02',
                'source': {
                    'path': GUIDE,
                    'source_date': '2024-03-06',
                    'sha256': digest,
                    'locator': f'table row {index}: {label}',
                },
                'details': {
                    'watch_id': key,
                    **resale_group(key, base, bounds, row[2]),
                    'priority': 'valuable_candidate',
                    'local_tier': None,
                    'guide_tier': row[1],
                    'build_count': 0,
                    'builds': [],
                    'build_contexts': [],
                    'native_conditions': {stat: {'min': low, 'max': high} for stat, (low, high) in bounds.items()},
                    'equal_stat_groups': [list(group) for group in equal],
                    'require_complete_capture': True,
                    **(
                        {
                            'planner_source': planner_sources[key],
                            **({'missing_zero_stats': ['7:0']} if key.startswith('plain-res-') else {}),
                        }
                        if key in planner_sources
                        else {}
                    ),
                    **({'required_affix_records': REQUIRED_AFFIXES[key]} if key in REQUIRED_AFFIXES else {}),
                    **({'raw_conditions': RAW_CONDITIONS[key]} if key in RAW_CONDITIONS else {}),
                    'roll_bucket': description,
                    'guide_conditions': quote,
                    'stat_priority': None,
                    'guide_source': {
                        'url': 'https://maxroll.gg/d2/items/valuable-magic-items',
                        'source_date': '2024-03-06',
                    },
                    'source_quote': row[2],
                    'nonladder_ask_reference': {'priced_sellers': 0, 'median_ist': None},
                    'market_priority': False,
                    'caveat': 'Combination demand from cached guide; not a Non-Ladder price or guaranteed sale.',
                },
            }
        )
    return result
