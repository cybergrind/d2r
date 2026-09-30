"""Reviewed equipment alternatives; mercenary use never transfers wearer stats."""

import json
from collections import defaultdict
from functools import lru_cache

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.base_use import UTILITY
from pricing.knowledge.assessment.maintenance.native_membership import unique_base_condition


MEMBERS = {
    'Wealth': {
        'role': 'Mercenary Find armor alternative',
        'kind': 'runeword',
        'types': ['tors'],
        'qualities': ['normal', 'superior', 'low_quality'],
        'important_stats': ['80:0', '79:0', '2:0'],
        'conditions': [
            'Mercenary Magic Find and Gold Find count on its credited killing blows, not '
            'every player kill. This armor supplies no resistance, attack speed or life '
            'leech; verify survival and whether the mercenary can secure kills.'
        ],
    },
    'Goldskin': {
        'kind': 'unique',
        'types': ['tors'],
        'qualities': ['unique'],
        'important_stats': ['39:0', '41:0', '43:0', '45:0', '16:0', '79:0'],
        'conditions': [
            'All resistance and defense support early mercenary survival. The mercenary '
            'gold bonus applies to its killing blows, not every player kill; this armor '
            'supplies no life leech.'
        ],
    },
    'Venom Ward': {
        'kind': 'unique',
        'types': ['tors'],
        'qualities': ['unique'],
        'important_stats': ['45:0', '46:0', '110:0', '16:0'],
        'conditions': [
            'Poison resistance, increased maximum poison resistance and poison length '
            'reduction are poison-specific protection. They do not supply other '
            'resistances or life leech; check the complete loadout and equipment '
            'requirements.'
        ],
    },
    'Hustle (armor)': {
        'kind': 'runeword',
        'types': ['tors'],
        'qualities': ['normal', 'superior', 'low_quality'],
        'important_stats': ['93:0', '96:0', '99:0', '39:0', '41:0', '43:0', '45:0'],
        'conditions': [
            'Armor attack speed, movement, hit recovery and resistance support the mercenary. '
            'Attack speed breakpoints depend on the weapon and complete loadout; no life leech is supplied. '
            'Evade effectiveness on a mercenary is not assumed. This assesses an existing completed item, '
            'not current Non-Ladder recipe creation availability.'
        ],
    },
    'Smoke': {
        'kind': 'runeword',
        'types': ['tors'],
        'qualities': ['normal', 'superior', 'low_quality'],
        'sockets': 2,
        'important_stats': ['39:0', '41:0', '43:0', '45:0', '99:0', '32:0'],
        'conditions': [
            'Resistance and hit recovery support survival; Smoke supplies no life leech. '
            'Energy does not increase mercenary life or useful mana, and the mercenary cannot use Weaken charges.'
        ],
    },
    'Duress': {
        'kind': 'runeword',
        'types': ['tors'],
        'qualities': ['normal', 'superior', 'low_quality'],
        'important_stats': ['136:0', '135:0', '17:0', '18:0', '99:0', '39:0', '41:0', '43:0', '45:0'],
        'conditions': [
            'Crushing Blow, Open Wounds and off-weapon damage need eligible attacks, not mercenary spells. '
            'Duress supplies no life leech.',
            'Cold damage can shatter corpses; consider Find Item or corpse-dependent skills before choosing Duress.',
        ],
    },
    'Rockstopper': {
        'kind': 'unique',
        'types': ['helm'],
        'qualities': ['unique'],
        'important_stats': ['36:0', '99:0', '39:0', '41:0', '43:0'],
        'conditions': [
            'Physical damage reduction, hit recovery and fire/lightning/cold resistance support survival. '
            'Vitality does not increase mercenary life; this helmet supplies no life leech or poison resistance.'
        ],
    },
    'Rockfleece': {
        'kind': 'unique',
        'types': ['tors'],
        'qualities': ['unique'],
        'important_stats': ['36:0', '34:0', '0:0'],
        'conditions': [
            'Physical damage reduction is the main survival benefit; resistance and life leech need other equipment.'
        ],
    },
    'Lionheart': {
        'kind': 'runeword',
        'types': ['tors'],
        'qualities': ['normal', 'superior', 'low_quality'],
        'important_stats': ['17:0', '18:0', '7:0', '0:0', '2:0', '39:0', '41:0', '43:0', '45:0'],
        'conditions': [
            'Life, resistances and off-weapon damage support the mercenary; '
            'this armor supplies no life leech or attack speed.'
        ],
    },
    'Temper': {
        'kind': 'runeword',
        'types': ['helm', 'circ'],
        'qualities': ['normal', 'superior', 'low_quality'],
        'important_stats': ['39:0', '142:0', '76:0', '99:0'],
        'conditions': [
            'Fire resistance and absorb address fire damage; other damage types and life leech need separate equipment.'
        ],
    },
    'Cure': {
        'kind': 'runeword',
        'types': ['helm', 'circ'],
        'qualities': ['normal', 'superior', 'low_quality'],
        'important_stats': ['151:109', '45:0', '110:0', '76:0', '99:0'],
        'conditions': [
            'Cleansing reduces curse and poison duration; healing through Prayer requires an actual Prayer mercenary. '
            'Cure alone does not establish the Prayer/Insight combination or supply life leech.'
        ],
    },
    'Ground': {
        'kind': 'runeword',
        'types': ['helm', 'circ'],
        'qualities': ['normal', 'superior', 'low_quality'],
        'important_stats': ['41:0', '144:0', '76:0', '99:0'],
        'conditions': [
            'Lightning resistance and absorb address lightning damage; other damage types and life leech '
            'need separate equipment. Vitality does not increase mercenary life.'
        ],
    },
    'Guardian Angel': {
        'kind': 'unique',
        'types': ['tors'],
        'qualities': ['unique'],
        'important_stats': ['40:0', '42:0', '44:0', '46:0'],
        'conditions': [
            'Raised resistance caps need actual resistance from the complete mercenary loadout. '
            'Paladin skills and shield-block bonuses are not mercenary benefits.'
        ],
    },
    "The Gladiator's Bane": {
        'kind': 'unique',
        'types': ['tors'],
        'qualities': ['unique'],
        'important_stats': ['34:0', '35:0', '153:0', '99:0', '110:0'],
        'conditions': [
            'Requires level 85. Physical and magic damage reduction are flat amounts, not percentages; '
            'Cannot Be Frozen preserves attack speed against ordinary chill.'
        ],
    },
    'Skin of the Flayed One': {
        'kind': 'unique',
        'types': ['tors'],
        'qualities': ['unique'],
        'important_stats': ['60:0', '74:0'],
        'conditions': [
            'Life leech needs eligible physical attack damage and is affected by monster drain effectiveness. '
            'Self-repair is unnecessary for mercenary durability.'
        ],
    },
    'The Face of Horror': {
        'kind': 'unique',
        'types': ['helm'],
        'qualities': ['unique'],
        'important_stats': ['0:0', '39:0', '41:0', '43:0', '45:0'],
        'conditions': [
            'Strength supports equipment requirements and resistance supports survival. '
            'Hit Causes Monster to Flee can scatter packs; this helmet supplies no life leech.'
        ],
    },
}


@lru_cache(maxsize=2)
def _legal_codes(raw):
    document = json.loads(raw)
    if document.get('schema_version') != 1:
        raise ValueError('Unsupported recipe utility schema')
    codes = defaultdict(set)
    for row in document['rows']:
        details = row.get('details', {})
        if row.get('kind') == 'base_rule' and details.get('legality') == 'verified_type_and_capacity':
            codes[details['runeword'], details['base_type']].add(row['base_code'])
    return {key: tuple(sorted(values)) for key, values in codes.items()}


def legal_base_condition(name, types):
    index = _legal_codes(read_artifact(UTILITY))
    codes = sorted({code for item_type in types for code in index.get((name, item_type), ())})
    if not codes:
        raise ValueError(f'No verified legal mercenary bases for {name}')
    return {'any': [{'op': 'fact_eq', 'field': 'base_code', 'value': code} for code in codes]}


def expand_merc_survival(row):
    name = row['item']
    if name not in MEMBERS or row['class'] not in CLASS_NAMES or row['side'] != 'merc':
        raise ValueError('Invalid mercenary survival template membership')
    member = MEMBERS[name]
    if row['slot'] != ('Body Armor' if member['types'] == ['tors'] else 'Helmet'):
        raise ValueError('Mercenary survival template has the wrong equipment slot')
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
    ]
    if member['kind'] == 'unique':
        must.append(unique_base_condition(name))
    else:
        must.extend(
            {'op': 'fact_eq', 'field': key, 'value': value}
            for key, value in [('runeword', name), ('sockets', member.get('sockets', 3)), ('socket_contents', 'filled')]
        )
        must.append(legal_base_condition(name, member['types']))
    return {
        **{key: value for key, value in row.items() if key not in ('template', 'item', 'class')},
        'role': member.get('role', 'Mercenary survival alternative'),
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': list(member['types']),
        'qualities': list(member['qualities']),
        'must': {'all': must},
        'important_stats': list(member['important_stats']),
        'conditions': [
            'Verify mercenary level, strength and dexterity requirements. '
            'Ethereal durability is safe on mercenaries; no automatic price premium is inferred.',
            *member['conditions'],
            *row.get('conditions', []),
        ],
    }


def expand_zeal_um_survival(row):
    """Exact reviewed socket alternatives from Zeal's Act 2 mid-game table."""
    if (
        row['item'] not in ('Guardian Angel', "The Gladiator's Bane", 'Rockstopper')
        or row['build'] != 'zeal-paladin'
        or row['class'] != 'Paladin'
    ):
        raise ValueError('Unreviewed Zeal Um survival alternative')
    role = expand_merc_survival(row)
    role['role'] = 'Act 2 survival alternative with Um'
    role['must']['all'].extend(
        [
            {'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 2 Might'},
            {'op': 'fact_eq', 'field': 'sockets', 'value': 1},
            {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'filled'},
            {'op': 'socket_runes_equal', 'value': ['Um Rune']},
        ]
    )
    role['important_stats'] = list(dict.fromkeys([*role['important_stats'], '39:0', '41:0', '43:0', '45:0']))
    if row['item'] == 'Rockstopper':
        role['conditions'] = [
            text.replace(
                'this helmet supplies no life leech or poison resistance.',
                'the unsocketed helmet supplies no life leech or poison resistance. Um adds poison resistance.',
            )
            for text in role['conditions']
        ]
    role['conditions'].append(
        'One verified Um supplies 15 all resistances in this armor or helmet. '
        'An empty socket or another filler is not this setup. Native roll maxima are preferences, '
        'not entry requirements. Mid-game table context: Act 2 Might; higher resistance caps '
        'still need enough resistance from the whole loadout.'
    )
    return role
