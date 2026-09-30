"""Source-specific completed armor examples; generic recipe/base utility stays separate."""

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.maintenance.aura_recipe_templates import recipe_condition


RES = ('39:0', '41:0', '43:0', '45:0')
EXAMPLES = {
    'treachery-mid': ('Treachery', 'Great Hauberk', False),
    'treachery-end': ('Treachery', 'Archon Plate', True),
    'duress-mid': ('Duress', 'Great Hauberk', False),
    'duress-end': ('Duress', 'Great Hauberk', True),
    'fortitude-end': ('Fortitude', 'Sacred Armor', True),
}
STATS = {
    'Treachery': ('93:0', '99:0', '43:0', '201:17103', '198:17807', '79:0'),
    'Duress': ('17:0', '18:0', '16:0', '99:0', '135:0', '136:0', '54:0', '55:0', *RES),
    'Fortitude': ('17:0', '18:0', '16:0', '201:3855', '216:0', '34:0', '74:0', '42:0', *RES),
}
NOTES = {
    'Treachery': [
        '45 IAS and 20 recovery come from the completed armor. Fade (5%, level 15 when struck) '
        'and Venom (25%, level 15 on striking) require their actual procs; Fade is not assumed active.',
        'Assassin skills do not improve this mercenary. Gold Find applies to its credited kills. '
        'The armor supplies no life leech; IAS breakpoints depend on the weapon and other gear.',
    ],
    'Duress': [
        'Off-weapon damage, Crushing Blow and Open Wounds support eligible physical attacks. '
        'Cold damage can shatter corpses; the armor supplies no life leech.',
        'Total recovery is 40 (20 from the word plus 20 from Shael). Um and Thul yield '
        '45 cold resistance and 15 to the other three elements.',
    ],
    'Fortitude': [
        '300% off-weapon damage supports physical attacks. 25 cast rate is not attack speed, '
        'and damage-to-mana is not a useful mercenary bonus.',
        'Chilling Armor is a 20% chance to cast level 15 when struck, not a guaranteed active buff. '
        'Life per level uses the mercenary level; Sol reduction, Dol replenishment and Lo maximum '
        'lightning resistance support survival. Actual resistance must still reach that raised cap.',
    ],
}


def expand_zeal_merc_word(row):
    slug = row['configuration']
    name, base_name, endgame = EXAMPLES[slug]
    if (row['build'], row['class'], row['side'], row['slot']) != ('zeal-paladin', 'Paladin', 'merc', 'Body Armor'):
        raise ValueError('Unreviewed Zeal mercenary armor word context')
    base = next(r for r in metadata()['bases'].values() if r['name'] == base_name)
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': 'Paladin'},
        {'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 2 Might'},
        {'op': 'fact_eq', 'field': 'base_code', 'value': base['code']},
        recipe_condition(name, ['tors']),
    ]
    preferences = []
    if endgame:
        must.append({'op': 'fact_eq', 'field': 'ethereal', 'value': True})
        preferences.append(
            {
                'label': 'Perfect total Enhanced Defense in the superior example',
                'when': {
                    'all': [
                        {'op': 'fact_eq', 'field': 'rarity', 'value': 'superior'},
                        {
                            'op': 'stat_at_least',
                            'key': '16:0',
                            'value': 15 if name == 'Treachery' else 215,
                            'absent_is_zero': True,
                        },
                    ]
                },
            }
        )
    return {
        **{k: v for k, v in row.items() if k not in ('configuration', 'class')},
        'role': ('Endgame' if endgame else 'Mid-game') + ' mercenary ' + name + ' / ' + base_name,
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': ['tors'],
        'base_codes': [base['code']],
        'qualities': ['normal', 'superior'],
        'must': {'all': must},
        'important_stats': list(STATS[name]),
        'preferences': preferences,
        'conditions': [
            *NOTES[name],
            "This is the guide's linked armor example, not a universal best-base claim. Check actual "
            'strength and level requirements and the complete survival setup. Other legal bases can '
            'still have recipe utility; an empty base is not this completed item.',
            'Ethereal is required for the cited endgame example. Superior defense and maximum word '
            'rolls are preferences, not minimum requirements.'
            if endgame
            else 'Non-ethereal and ethereal versions both retain the mid-game armor effects.',
        ],
    }
