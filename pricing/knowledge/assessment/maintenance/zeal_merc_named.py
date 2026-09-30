"""Reviewed named mercenary equipment and linked socket configurations for Zeal."""

from pricing.knowledge.assessment.maintenance.native_membership import named_base_condition


RES = ('39:0', '41:0', '43:0', '45:0')
MEMBERS = {
    'shaftstop-um': ('Shaftstop', 'unique', 'Body Armor', ('36:0', '7:0', '32:0', '16:0', *RES), 'Um Rune'),
    'duriel-um': (
        "Duriel's Shell",
        'unique',
        'Body Armor',
        ('153:0', '0:0', '216:0', '214:0', '16:0', *RES),
        'Um Rune',
    ),
    'tal-amethyst': ("Tal Rasha's Horadric Crest", 'set', 'Helmet', ('60:0', '7:0', '0:0', *RES), 'Perfect Amethyst'),
    'guillaume-ias': ("Guillaume's Face", 'set', 'Helmet', ('136:0', '141:0', '99:0', '0:0', '93:0'), 'ias'),
    'gaze-ias': ('Vampire Gaze', 'unique', 'Helmet', ('60:0', '36:0', '35:0', '16:0', '54:0', '55:0', '93:0'), 'ias'),
    'stealskull-ias': ('Stealskull', 'unique', 'Helmet', ('60:0', '99:0', '93:0', '80:0', '16:0'), 'ias'),
    'kira-ral': ("Kira's Guardian", 'unique', 'Helmet', (*RES, '153:0', '99:0'), 'Ral Rune'),
    'guillaume-cham': ("Guillaume's Face", 'set', 'Helmet', ('136:0', '141:0', '99:0', '0:0', '153:0'), 'Cham Rune'),
    'gaze-scintillating': (
        'Vampire Gaze',
        'unique',
        'Helmet',
        ('60:0', '36:0', '35:0', '16:0', '54:0', '55:0', '93:0', *RES),
        'scintillating',
    ),
}
NOTES = {
    'Shaftstop': (
        '30% physical reduction and life aid survival; missile defense is situational. Other gear must supply '
        'leech and elemental protection.'
    ),
    "Duriel's Shell": (
        'Strength, resistances and Cannot Be Frozen aid survival. Level-scaled life and defense depend on the '
        'mercenary level, not the player level; this armor supplies no leech.'
    ),
    "Tal Rasha's Horadric Crest": (
        'Life leech, life and resistances aid survival. The perfect amethyst supplies 10 Strength for '
        'equipment requirements. Mana and mana leech do not benefit the mercenary.'
    ),
    "Guillaume's Face": (
        'Crushing Blow, Deadly Strike, Strength and hit recovery support physical attacks. This helmet '
        'supplies neither life leech nor elemental resistance.'
    ),
    'Vampire Gaze': (
        'Life leech, physical reduction and flat magic reduction support survival. Mana leech is not useful '
        'to the mercenary. Cold damage may shatter corpses; upgraded defense is not automatically better.'
    ),
    'Stealskull': (
        'The helmet has 10 native IAS; its jewel adds 15. Leech and hit recovery aid survival. Mercenary '
        'Magic Find applies to its credited kills. Mana leech is not a useful mercenary bonus.'
    ),
    "Kira's Guardian": (
        'Cannot Be Frozen, recovery and all resistances aid survival; Ral adds 30 fire resistance in this '
        'helmet. This does not supply life leech.'
    ),
}


def expand_zeal_merc_named(row):
    slug = row['configuration']
    name, quality, slot, stats, filler = MEMBERS[slug]
    if (row['build'], row['class'], row['side'], row['slot']) != ('zeal-paladin', 'Paladin', 'merc', slot):
        raise ValueError('Unreviewed Zeal named mercenary context')
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': 'Paladin'},
        {'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 2 Might'},
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
        named_base_condition(name, quality),
        {'op': 'fact_eq', 'field': 'sockets', 'value': 1},
        {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'filled'},
    ]
    if quality == 'set':
        must.append({'op': 'fact_eq', 'field': 'ethereal', 'value': False})
    if filler in ('ias', 'scintillating'):
        thresholds = {'93:0': 15}
        if filler == 'scintillating':
            thresholds.update(dict.fromkeys(RES, 11))
            must.append({'op': 'fact_eq', 'field': 'ethereal', 'value': True})
        must.append({'op': 'socket_jewel_matches', 'stats': thresholds, 'count': 1})
    else:
        must.append(
            {'op': 'socket_gems_equal' if filler == 'Perfect Amethyst' else 'socket_runes_equal', 'value': [filler]}
        )
    preferences = []
    if filler == 'scintillating':
        preferences.append(
            {
                'label': 'Perfect Scintillating jewel: 15 IAS and 15 all resistances',
                'when': {'op': 'socket_jewel_matches', 'stats': {'93:0': 15, **dict.fromkeys(RES, 15)}, 'count': 1},
            }
        )
    return {
        **{k: v for k, v in row.items() if k not in ('configuration', 'class')},
        'role': 'Mercenary equipment: '
        + name
        + ' / '
        + {'ias': '15 IAS jewel', 'scintillating': '15 IAS / resistance jewel'}.get(
            filler, filler.removesuffix(' Rune')
        ),
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': ['tors'] if slot == 'Body Armor' else (['circ'] if name == "Kira's Guardian" else ['helm']),
        'qualities': [quality],
        'must': {'all': must},
        'important_stats': list(stats),
        'preferences': preferences,
        'conditions': [
            NOTES[name],
            'Check the actual equipment requirements and full attack-speed, leech and survival loadout.',
            *(
                ['15 IAS and 11-15 all resistances must occur together on the same socketed jewel.']
                if filler == 'scintillating'
                else ['Socketed Um adds 15 all resistances.']
                if filler == 'Um Rune'
                else ['Socketed Cham adds Cannot Be Frozen.']
                if filler == 'Cham Rune'
                else []
            ),
        ],
    }
