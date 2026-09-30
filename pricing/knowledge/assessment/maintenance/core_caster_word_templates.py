"""Reviewed core casting recipes: recipient and swap semantics stay explicit."""

from pricing.knowledge.assessment.maintenance.merc_survival_templates import legal_base_condition
from pricing.knowledge.definition_store import catalog


BUILDS = {
    'zeal-paladin': 'Paladin',
    'blood-boil-warlock-guide': 'Warlock',
    'summoner-warlock-guide': 'Warlock',
    'fire-wall-sorceress-guide': 'Sorceress',
    'frozen-orb-meteor-sorceress': 'Sorceress',
    'frozen-orb-sorceress': 'Sorceress',
    'hydra-sorceress': 'Sorceress',
    'summoner-necromancer-guide': 'Necromancer',
}


def stat(key, value):
    return {'op': 'stat_at_least', 'key': key, 'value': value, 'absent_is_zero': True}


def expand_core_caster_word(row):
    name, slot = row['item'], row['slot'].replace(' ', '-')
    zeal = row['build'] == 'zeal-paladin'
    if zeal and (name, slot) not in {('Call to Arms', 'Weapon-Swap'), ('Spirit', 'Off-Hand-Swap')}:
        raise ValueError('Unreviewed Zeal swap recipe or slot')
    if BUILDS.get(row['build']) != row['class'] or row['side'] != 'player':
        raise ValueError('Unreviewed core caster recipe wearer')
    shield = name == 'Spirit' and slot in ('Off-Hand', 'Off-Hand-Swap')
    if name == 'Spirit' and slot in ('Weapon', 'Off-Hand', 'Off-Hand-Swap'):
        types = (['shie', 'ashd'] if zeal else ['shie']) if shield else ['swor']
        keys = ['127:0', '105:0', '99:0', '9:0', '3:0', '147:0', '32:0']
        if shield:
            keys += ['41:0', '43:0', '45:0']
            if zeal:
                keys.append('39:0')
        conditions = [
            'Spirit shield runes grant cold, lightning and poison resistance, not fire resistance. '
            'Sword rune attack damage and leech do not increase spells or summons. '
            'Casting and recovery breakpoints require the complete loadout.'
        ]
        preferences = [{'label': '35 Faster Cast Rate', 'when': stat('105:0', 35)}]
    elif name == 'Heart of the Oak' and slot == 'Weapon':
        types = ['mace', 'staf']
        keys = ['127:0', '105:0', '77:0', '39:0', '41:0', '43:0', '45:0', '74:0', '2:0']
        conditions = [
            'Casting skill, mana and resistance utility applies without attacking. '
            'Mana leech and added attack damage do not benefit spells; charged Oak Sage '
            'and Raven are not passive equipped bonuses.'
        ]
        preferences = [
            {'label': '40 all resistances', 'when': {'all': [stat(k, 40) for k in ('39:0', '41:0', '43:0', '45:0')]}}
        ]
    elif name == 'Call to Arms' and slot == 'Weapon-Swap':
        # Unrestricted native weapon types; class-exclusive weapons are not inferred.
        types = ['swor', 'axe', 'mace', 'hamm', 'pole', 'spea', 'staf', 'scep', 'bow', 'xbow']
        keys = ['97:149', '97:155', '127:0']
        conditions = [
            'Switch to this weapon set and cast Battle Command, then Battle Orders; '
            'the captured weapon does not prove either buff is active. Additional skill '
            'levels from a swap shield require an actual compatible companion. '
            'Damage, IAS and Battle Cry are not priorities for this prebuff role.'
        ]
        preferences = [{'label': '+6 Battle Orders native roll', 'when': stat('97:149', 6)}]
    else:
        raise ValueError('Unreviewed core caster recipe or slot')
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
        *[
            {'op': 'fact_eq', 'field': key, 'value': value}
            for key, value in (
                ('identified', True),
                ('runeword', name),
                ('sockets', len(catalog().runewords[name]['runes'])),
                ('socket_contents', 'filled'),
            )
        ],
        legal_base_condition(name, types),
    ]
    if row.get('base_codes'):
        must.append({'any': [{'op': 'fact_eq', 'field': 'base_code', 'value': code} for code in row['base_codes']]})
    if shield:
        must.append({'op': 'fact_eq', 'field': 'ethereal', 'value': False})
        conditions.append(
            'Sustained shield use requires repairability. This shield requires a compatible main-hand weapon; '
            'it is not a Warlock Book.'
        )
    else:
        conditions.append(
            'Ethereal spell casting and prebuffing do not consume weapon durability; melee attacks are a separate '
            'concern. No ethereal price premium is inferred.'
        )
    if name == 'Call to Arms':
        must += [stat('97:149', 1), stat('97:155', 2)]
    if name in ('Heart of the Oak', 'Call to Arms'):
        conditions.append(
            'Two-handed weapon bases need a compatible equipment setup; the Warlock exception requires '
            'an actual Book off-hand.'
        )
    if zeal:
        conditions.append(
            'The Zeal guide casts Battle Command twice, then Battle Orders on the swap. Enigma Teleport '
            'uses this casting set; return to the main weapon for Zeal. FCR is not attack speed. '
            'Spirit all-skills can strengthen Call to Arms only with an actual compatible equipped '
            'one-handed companion; no companion or active buff is inferred from this item alone.'
        )
        if shield:
            conditions.append(
                'Native Paladin shield resistance is separate from Spirit rune resistance. Any observed '
                'fire resistance comes from another contribution, not the Spirit recipe. Defense and '
                'block chance depend on the base and full wearer setup.'
            )
    if slot.endswith('Swap'):
        conditions.append(
            'Item bonuses apply only while this weapon set is active; an inactive swap grants no equipped stats.'
        )
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': 'Battle Orders and Battle Command prebuff'
        if name == 'Call to Arms'
        else 'Caster recipe shield alternative'
        if shield
        else 'Caster recipe weapon alternative',
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': types,
        'qualities': ['normal', 'superior', 'low_quality'],
        'must': {'all': must},
        'important_stats': keys,
        'preferences': preferences,
        'conditions': conditions,
    }
