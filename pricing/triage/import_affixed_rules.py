"""Guide and cached-ask affixed patterns, without invented numerical prices."""

import json
from itertools import combinations

from pricing.knowledge.refresh import atomic_json
from pricing.triage.build import ROOT
from pricing.triage.patterns import support_pattern


SOURCE = 'guides/pricing.html §2 blue/yellow/orange'
CLASS_SKILLS = ('453', '514', '498', '442', '403', '488', '519', '1862')
RESISTS = ('427', '428', '426', '401')


def stats(**values):
    return {'properties': {key: {'min': value} for key, value in values.items()}}


def counted(count, *options):
    return {'at_least': {'count': count, 'of': list(options)}}


def resist(value):
    return counted(1, *(stats(**{prop: value}) for prop in RESISTS))


def magic_patterns(add):
    # Guide §8: Echoing throwing weapons are paid buff-switch items even
    # without a suffix. Plain Javelin tree skills are not the same use.
    for family in ('jave', 'tkni', 'taxe'):
        add(
            family,
            'magic',
            'Echoing throwing weapon: +3 Warcries for buff switch',
            {
                **stats(**{'406': 3}),
                'bucket': 'echoing-switch',
                'band_facets': ['base_code', 'ethereal', 'base_modifiers'],
                'compare_property': '457',
                'compare_range': {'min': 0, 'max': 40},
                'compare_label': 'IAS',
                'compare_modifier_facet': 'base_modifiers',
                'compare_missing': 0,
            },
            source='guides/pricing.html §8 Echoing throwing weapons; scoped cached asks 2026-10-03',
        )
    # Guide §2 patterns; suffix bounds verified in local d2data magicsuffix.json.
    for skill in CLASS_SKILLS:
        for prop, minimum, suffix in (
            ('418', 81, 'Whale'),
            ('520', 10, 'Apprentice'),
            ('461', 26, 'Luck'),
            ('526', 1, 'Teleportation'),
        ):
            add('amul', 'magic', f'Class skills + {suffix}', stats(**{skill: 2, prop: minimum}))
    # Full tree-prefix/Magus combinations found in scoped paid asks. Other
    # trees have only isolated asks and do not inherit this demand signal.
    for skill, label, sellers in (
        ('515', 'Fire Skills (Sorceress)', 2),
        ('516', 'Lightning Skills (Sorceress)', 3),
        ('517', 'Cold Skills (Sorceress)', 5),
        ('443', 'Combat Skills (Paladin)', 6),
        ('500', 'Poison and Bone Skills', 6),
        ('1547', 'Eldritch Skills', 3),
        ('1548', 'Chaos Skills', 3),
    ):
        add(
            'circ',
            'magic',
            f'Magic circlet: +3 {label} + 20 FCR',
            stats(**{skill: 3, '520': 20}),
            source={
                'path': 'pricing/raw/traderie/pull-20261003/',
                'reviewed_at': '2026-10-03',
                'scope': 'SC/NL/PC/RotW',
                'kind': 'paid_pattern',
                'independent_sellers': sellers,
            },
        )
    # At least 31 MF requires both the prefix and suffix on a magic ring.
    add('ring', 'magic', 'Fortuitous ring of Fortune: 31+ magic find', stats(**{'461': 31}))
    for prop, minimum, suffix in (('480', 30, 'Speed'), ('461', 26, 'Luck'), ('418', 81, 'Whale')):
        add(
            'circ',
            'magic',
            f"Artisan's circlet of {suffix}",
            {**stats(**{prop: minimum}), 'conditions': {'sockets': 3, 'base_name': {'in': ['Tiara', 'Diadem']}}},
        )
    add(
        'shie',
        'magic',
        "Jeweler's Monarch of Deflecting",
        {**stats(**{'446': 20, '449': 30}), 'conditions': {'sockets': 4, 'base_name': 'Monarch'}},
    )
    for prop, minimum, suffix in (('418', 90, 'Whale'), ('430', 24, 'Stability'), ('429', 10, 'Precision')):
        add(
            'tors',
            'magic',
            f"Jeweler's elite armor of {suffix}",
            {
                **stats(**{prop: minimum}),
                'conditions': {
                    'sockets': 4,
                    'base_name': {'in': ['Archon Plate', 'Dusk Shroud', 'Wire Fleece', 'Sacred Armor']},
                },
            },
        )


def physical_weapon_patterns(add):
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.mechanics.base_tiers import base_tier

    # Shared physical patterns supported by scoped 2026-10-03 asks. These
    # are review candidates, not sufficient evidence for a numerical price.
    sellers = {'swor': 8, 'axe': 8, 'mace': 5, 'club': 2, 'spea': 2, 'bow': 10, 'xbow': 3}
    for family, count in sellers.items():
        bases = sorted(
            b['name'] for b in metadata()['bases'].values() if b['type'] == family and base_tier(b['code']) == 'Elite'
        )
        ranged = family in ('bow', 'xbow')
        conditions = {'base_name': {'in': bases}}
        support = None
        if not ranged:
            # Phase Blades supply durability intrinsically, including non-ethereal
            # copies. Other melee bases still need ethereal damage and a remedy.
            support = counted(
                1,
                {'conditions': {'base_name': 'Phase Blade', 'ethereal': {'in': [False, True]}}},
                {
                    'conditions': {'ethereal': True},
                    **counted(
                        1,
                        stats(**{'431': 1}),
                        {'properties': {'432': True}},
                        {'conditions': {'sockets': {'min': 1}}},
                    ),
                },
            )
        add(
            family,
            'rare',
            'Elite physical weapon: damage + speed' + ('' if ranged else ' + durability solution'),
            {**stats(**{'510': 300, '457': 20 if ranged else 30}), 'conditions': conditions},
            support,
            source={
                'path': 'pricing/raw/traderie/pull-20261003/',
                'reviewed_at': '2026-10-03',
                'scope': 'SC/NL/PC/RotW',
                'kind': 'paid_pattern',
                'independent_sellers': count,
            },
        )
        if family in ('swor', 'axe', 'mace'):
            add(
                family,
                'rare',
                "Elite Fool's weapon: scaling damage and attack rating + damage + speed + durability solution",
                {
                    **stats(**{'510': 200, '457': 30, '535': 1, '536': 1}),
                    'conditions': conditions,
                },
                support,
                source={
                    'path': 'pricing/raw/traderie/pull-20261003/',
                    'reviewed_at': '2026-10-03',
                    'scope': 'SC/NL/PC/RotW',
                    'kind': 'paid_pattern',
                    'independent_sellers': {'swor': 9, 'axe': 5, 'mace': 2}[family],
                    'observed_ed_band': [200, 299],
                },
            )


def throwing_weapon_patterns(add):
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.mechanics.base_tiers import base_tier

    # Double Throw's mastery replenishes quantity on critical strikes. Unlike
    # melee durability or Amazon throwing use, a replenish affix is not required.
    for family in ('taxe', 'tkni', 'jave'):
        for elite in (True, False):
            bases = sorted(
                b['name']
                for b in metadata()['bases'].values()
                if b['type'] == family and base_tier(b['code']) in (('Elite',) if elite else ('Normal', 'Exceptional'))
            )
            add(
                family,
                'rare',
                'Double Throw: ethereal damage + speed' + ('; review upgrade costs' if not elite else ''),
                {
                    **stats(**{'510': 300, '457': 30}),
                    'conditions': {'ethereal': True, 'base_name': {'in': bases}},
                },
                source={
                    'guide': 'pricing/raw/mr/guides__double-throw-barbarian-guide.html',
                    'market': 'pricing/raw/traderie/',
                    'reviewed_at': '2026-10-03',
                    'scope': 'SC/NL/PC/RotW',
                    'kind': 'paid_pattern',
                    'query': 'rare throwing weapons, ethereal, ED >= 300, IAS >= 30',
                },
            )


def affixed_rules():
    rows = []

    def add(family, rarity, label, required, support=None, source=SOURCE, low_rolls=None, labels=None):
        rows.append(
            {
                'family': family,
                'category': rarity,
                **required,
                **(support or {}),
                'pattern': {
                    **support_pattern(support or {}),
                    'properties': required.get('properties', {}) | (low_rolls or {}),
                },
                **({'labels': labels} if labels else {}),
                'pattern_label': label,
                'source': source,
                'imported_affixed_rule': True,
            }
        )

    caster_support = counted(
        2, resist(10), stats(**{'418': 1}), stats(**{'400': 1}), stats(**{'437': 1}), stats(**{'429': 1})
    )
    for rarity in ('rare', 'crafted'):
        add('ring', rarity, 'Caster ring: FCR + two supporting affixes', stats(**{'520': 10}), caster_support)
    add(
        'ring',
        'rare',
        'Caster ring: FCR + two resistances + magic find',
        stats(**{'520': 10}),
        counted(2, counted(2, *(stats(**{p: 10}) for p in RESISTS)), stats(**{'461': 10})),
        source='User CHECK label 2026-10-03: corpus 2d289b42b674 (Corruption Knot)',
    )
    for rarity in ('rare', 'crafted'):
        add(
            'ring',
            rarity,
            'Melee ring: attack rating + leech + two supporting affixes',
            stats(**{'423': 100, '462': 5}),
            counted(2, stats(**{'441': 10}), stats(**{'418': 30}), stats(**{'437': 10}), stats(**{'429': 10})),
        )
    for skill in CLASS_SKILLS:
        add(
            'amul',
            'rare',
            'Caster amulet: class skills + FCR + two supporting affixes',
            stats(**{skill: 2, '520': 10}),
            counted(
                2,
                resist(15),
                stats(**{'418': 40}),
                stats(**{'400': 1}),
                stats(**{'526': 1}),
                stats(**{'437': 1}),
                stats(**{'429': 1}),
            ),
            source={
                'guide': SOURCE,
                'path': 'pricing/raw/traderie/',
                'reviewed_at': '2026-10-04',
                'scope': 'SC/NL/PC/RotW',
                'kind': 'paid_pattern',
                'mana_support_independent_sellers': 10,
            },
        )
        add(
            'amul',
            'crafted',
            'Caster craft: class skills + 20 FCR',
            stats(**{skill: 2, '520': 20}),
            low_rolls={'520': {'min': 15}},
            labels={'520': 'faster cast rate'},
            source={
                'guide': SOURCE,
                'path': 'pricing/raw/traderie/',
                'recipe': 'third-parties/d2data/json/cubemain.json#Caster Amulet',
                'reviewed_at': '2026-10-04',
                'scope': 'SC/NL/PC/RotW',
                'kind': 'paid_pattern',
                'low_fcr_independent_sellers': {
                    '453': 4,
                    '514': 2,
                    '498': 3,
                    '442': 4,
                    '403': 2,
                    '488': 3,
                    '519': 3,
                    '1862': 2,
                }[skill],
            },
        )
        add(
            'amul',
            'crafted',
            'Caster craft: class skills + 10 FCR + two useful extras',
            stats(**{skill: 2, '520': 10}),
            counted(
                2, resist(15), stats(**{'418': 30}), stats(**{'437': 10}), stats(**{'429': 10}), stats(**{'526': 1})
            ),
            source='guides/pricing-primer.html#d6',
        )
        add('circ', 'magic', 'Magic circlet: class skills + 20 FCR', stats(**{skill: 2, '520': 20}))
        add(
            'circ',
            'rare',
            'Rare circlet: class skills + 20 FCR + two supporting affixes',
            stats(**{skill: 2, '520': 20}),
            counted(
                2,
                stats(**{'480': 1}),
                stats(**{'457': 1}),
                {'conditions': {'sockets': {'min': 1}}},
                resist(1),
                stats(**{'418': 1}),
                stats(**{'400': 1}),
                stats(**{'437': 1}),
                stats(**{'429': 1}),
            ),
        )
    for skill in ('454', '456', '410'):
        add(
            'glov',
            'magic',
            'Skill gloves + 20 IAS',
            {
                **stats(**{skill: 3, '457': 20}),
                'bucket': 'skill-gloves-20-ias',
                'band_facets': ['base_code', 'ethereal', 'sockets', 'socket_contents', 'base_modifiers'],
            },
        )
        add(
            'glov',
            'rare',
            'Rare skill gloves + 20 IAS + two supporting affixes',
            stats(**{skill: 2, '457': 20}),
            counted(2, stats(**{'437': 1}), stats(**{'429': 1}), stats(**{'418': 1}), stats(**{'462': 1}), resist(1)),
        )
    for rarity in ('rare', 'crafted'):
        source = (
            SOURCE
            if rarity == 'rare'
            else {
                'path': 'pricing/raw/traderie/',
                'reviewed_at': '2026-10-03',
                'scope': 'SC/NL/PC/RotW',
                'kind': 'paid_pattern',
                'guide': 'guides/pricing.html §2 crafted boots and belts',
            }
        )
        add(
            'boot',
            rarity,
            'Fast boots + two high resistances',
            stats(**{'480': 30}),
            counted(2, *(stats(**{prop: 25}) for prop in RESISTS)),
            source=source,
        )
        add(
            'belt',
            rarity,
            'FHR belt + life + strength and resistance',
            stats(**{'430': 24, '418': 40}),
            counted(2, resist(1), stats(**{'437': 1})),
            source=source,
        )
    add(
        'glov',
        'crafted',
        'Blood gloves: leech + crushing blow + life + speed or skills',
        stats(**{'462': 1, '567': 5, '418': 1}),
        counted(1, stats(**{'457': 20}), *(stats(**{p: 2}) for p in ('454', '456', '410'))),
    )
    # Scoped 2026-10-03 asks independently support these complete socketed
    # patterns; do not make mobility items pass by removing the caster's FCR gate.
    for prop, minimum, sellers in (
        ('520', 20, {'403': 8, '442': 6, '453': 11, '488': 11, '498': 7, '514': 9, '519': 7}),
        ('480', 30, {'453': 6, '488': 5, '519': 3}),
    ):
        for skill, count in sellers.items():
            add(
                'circ',
                'rare',
                'Two-socket class circlet + ' + ('20 FCR' if prop == '520' else '30 FRW'),
                {**stats(**{skill: 2, prop: minimum}), 'conditions': {'sockets': 2}},
                source={
                    'path': 'pricing/raw/traderie/pull-20261003/',
                    'reviewed_at': '2026-10-03',
                    'scope': 'SC/NL/PC/RotW',
                    'kind': 'paid_pattern',
                    'independent_sellers': count,
                    'query': {
                        'category': 'rare',
                        'family': 'circ',
                        'class_property': skill,
                        'support_property': prop,
                        'minimum': minimum,
                        'sockets': 2,
                    },
                },
            )
    for skill in ('456', '410', '454', '455'):
        extra = counted(1, stats(**{'437': 1}), stats(**{'429': 1}), resist(1)) if skill in ('454', '455') else None
        add(
            'glov',
            'rare',
            'Skill gloves: 20 IAS + mana leech',
            {
                **stats(**{skill: 2, '457': 20, '463': 3}),
                'bucket': 'rare-skill-gloves-mana-leech',
                'band_facets': ['base_code', 'ethereal', 'sockets', 'socket_contents', 'base_modifiers'],
                'compare_property': '428',
                'compare_range': {'min': 5, 'max': 30},
                'compare_label': 'lightning resistance',
                'compare_modifier_facet': 'base_modifiers',
            },
            extra,
            low_rolls={'463': {'min': 1}},
            labels={'463': 'mana leech'},
            source={
                'path': 'pricing/raw/traderie/pull-20261003/',
                'reviewed_at': '2026-10-03',
                'scope': 'SC/NL/PC/RotW',
                'kind': 'paid_pattern',
                'query': {
                    'category': 'rare',
                    'family': 'glov',
                    'skill_property': skill,
                    'skill': 2,
                    'ias': 20,
                    'mana_leech': 3,
                    'extra_strength_dexterity_or_resistance': extra is not None,
                },
            },
        )
    add(
        'amul',
        'rare',
        'Warlock teleport amulet: skills, leech, life and all resistances',
        stats(**{'1862': 2, '463': 7, '418': 30, '441': 10, '526': 1}),
        source='guides/pricing-primer.html#s6-1 (RR-pc-warlock-tele-amulet)',
    )
    jewel_stats = {'510': (20, 'enhanced damage'), '441': (8, 'all resistances'), '448': (10, 'maximum damage')}
    for pair in combinations(jewel_stats, 2):
        add(
            'jewl',
            'rare',
            'Rare jewel: ' + ' + '.join(jewel_stats[p][1] for p in pair),
            stats(**{p: jewel_stats[p][0] for p in pair}),
            low_rolls={p: {'min': 1} for p in pair},
            labels={p: jewel_stats[p][1] for p in pair},
            source='guides/pricing-primer.html#d3 (JW-rare / pairs of paid jewel stats)',
        )
    magic_patterns(add)
    physical_weapon_patterns(add)
    throwing_weapon_patterns(add)
    return rows


def main():
    path = ROOT / 'pricing/data/triage/rules.json'
    document = json.loads(path.read_text())
    rows = affixed_rules()
    document['rows'] = [r for r in document['rows'] if not r.get('imported_affixed_rule')] + rows
    atomic_json(path, document)
    print(
        json.dumps(
            {
                'affixed_rules': len(rows),
                'price_patterns': sum(bool(r.get('bucket')) for r in rows),
                'new_types_enabled': 0,
            }
        )
    )


if __name__ == '__main__':
    main()
