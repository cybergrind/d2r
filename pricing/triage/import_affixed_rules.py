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
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.mechanics.base_tiers import base_tier

    for prop, label in (('1546', 'Demon Skills'), ('1547', 'Eldritch Skills'), ('1548', 'Chaos Skills')):
        add(
            'grim',
            'magic',
            f'Magic grimoire: +3 {label}',
            stats(**{prop: 3}),
            source='guides/pricing-primer.html#s2-4 BS-grimoire magic tree-prefix bracket',
        )

    for prop, minimum, label in [('418', 81, 'life'), ('461', 26, 'magic find')]:
        add(
            'circ',
            'magic',
            'Warlock magic circlet: +2 skills + ' + label,
            stats(**{'1862': 2, prop: minimum}),
            source='guides/warlock.html#s4 Forbidden Diadem; native Whale/Luck suffix ranges',
        )
    add(
        'lcha',
        'magic',
        'Sharp Grand Charm: maximum damage + attack rating',
        stats(**{'448': 8, '423': 49}),
        source='guides/pricing-primer.html#s4-1 CH-gc-melee; native magicprefix Sharp 253',
    )
    large_source = 'pricing/raw/mr/items__valuable-magic-items.html Large Charms; qx0106eh items 84-92'
    for label, required in (
        (
            'Sharp: damage + attack rating',
            {'properties': {'448': {'min': 4, 'max': 8}, '423': {'min': 21, 'max': 48}}},
        ),
        ('Shimmering: all resistances', stats(**dict.fromkeys(RESISTS, 7))),
        ('mana + life', stats(**{'400': 20, '418': 30})),
    ):
        add('mcha', 'magic', 'Large Charm: ' + label, required, source=large_source)
    for prop in RESISTS:
        add(
            'mcha',
            'magic',
            'Large Charm: single resistance + life',
            stats(**{prop: 13, '418': 30}),
            source=large_source,
        )

    add(
        'scha',
        'magic',
        'Small Charm: magic find',
        stats(**{'461': 6}),
        source='guides/pricing-primer.html §4.2 CH-sc-mf',
    )
    add(
        'scha',
        'magic',
        'Fine Small Charm: maximum damage + attack rating',
        stats(**{'448': 3, '423': 20}),
        low_rolls={'448': {'min': 1}, '423': {'min': 1}},
        source='guides/pricing-primer.html §4.2 CH-sc-dmg; PLAN §3.9',
    )

    add(
        'scha',
        'magic',
        'Pestilent Small Charm: poison damage; niche trade review',
        stats(**{'518': 175}),
        source='pricing/raw/mr/items__valuable-magic-items.html elemental-damage; native Pestilent prefix 661',
    )
    add(
        'scha',
        'magic',
        'Shocking Small Charm of Vita: lightning damage + life; niche trade review',
        stats(**{'479': 44, '418': 16}),
        source=(
            'pricing/raw/mr/items__valuable-magic-items.html elemental-damage; '
            'qx0106eh item 117; native Shocking prefix 649'
        ),
    )

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
    # Explicit single-affix trade patterns in primer §3.2. These establish
    # review thresholds only; compound jewel asks must not price a plain copy.
    for prop, minimum, label in (
        ('510', 30, 'enhanced damage'),
        ('457', 15, 'increased attack speed'),
        ('441', 10, 'all resistances'),
    ):
        add(
            'jewl',
            'magic',
            f'Magic jewel: {label}',
            stats(**{prop: minimum}),
            source='guides/pricing-primer.html#s3-2 (JW-ed / JW-ias / JW-res)',
        )
    # An all-resistance prefix + Carnage suffix is a legal magic-jewel pair.
    # Guide §2 blue / primer D-3 specify both modifiers; no scoped price is implied.
    add(
        'jewl',
        'magic',
        'Magic jewel: all resistances + maximum damage',
        stats(**{'441': 8, '448': 10}),
        low_rolls={'441': {'min': 1}, '448': {'min': 1}},
        labels={'441': 'all resistances', '448': 'maximum damage'},
        source='guides/pricing.html#s2-blue; guides/pricing-primer.html#d3',
    )
    # At least 31 MF requires both the prefix and suffix on a magic ring.
    add('ring', 'magic', 'Fortuitous ring of Fortune: 31+ magic find', stats(**{'461': 31}))
    for family, bases, sockets in (
        ('tors', ['Archon Plate'], 4),
        ('circ', ['Tiara', 'Diadem'], 3),
    ):
        add(
            family,
            'magic',
            f'Magic socket base: {sockets} sockets; evaluate the suffix separately',
            {'conditions': {'base_name': {'in': bases}, 'sockets': sockets}},
            source='guides/pindle-anya.html#s5 (plain magic socket bases)',
        )
    add(
        'circ',
        'magic',
        'Tiara: faster run/walk + all resistances',
        {**stats(**{'480': 30, '441': 30}), 'conditions': {'base_name': 'Tiara'}},
        low_rolls={'480': {'min': 1}, '441': {'min': 1}},
        labels={'480': 'faster run/walk', '441': 'all resistances'},
        source='guides/pindle-anya.html#s5 (30 FRW + 30 all resistances)',
    )
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
        "Jeweler's Monarch: four sockets; evaluate the suffix separately",
        {'conditions': {'sockets': 4, 'base_name': 'Monarch'}},
        source='guides/pricing-primer.html#s3-3 (non-Deflecting four-socket Monarch)',
    )
    add(
        'shie',
        'magic',
        "Jeweler's Monarch of Deflecting",
        {**stats(**{'446': 20, '449': 30}), 'conditions': {'sockets': 4, 'base_name': 'Monarch'}},
    )
    add(
        'ashd',
        'magic',
        "Jeweler's Sacred Targe of Deflecting",
        {**stats(**{'446': 20, '449': 30}), 'conditions': {'sockets': 4, 'base_name': 'Sacred Targe'}},
    )
    elite_armor = sorted(
        base['name']
        for base in metadata()['bases'].values()
        if base['type'] == 'tors' and base_tier(base['code']) == 'Elite'
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
                    'base_name': {'in': elite_armor},
                },
            },
        )


def physical_weapon_patterns(add):
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.mechanics.base_tiers import base_tier

    # Shared physical patterns supported by scoped 2026-10-03 asks. These
    # are review candidates, not sufficient evidence for a numerical price.
    sellers = {'swor': 8, 'axe': 8, 'mace': 5, 'club': 2, 'spea': 2, 'bow': 10, 'xbow': 3}
    # Hammers are a separate native type within the guide's mace weapon class.
    # Only the guide-backed Fool's combination is added for them, without a price.
    for family, count in (sellers | {'hamm': None}).items():
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
        if count is not None:
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
        if family in ('swor', 'axe', 'mace', 'hamm'):
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
                    'independent_sellers': {'swor': 9, 'axe': 5, 'mace': 2}.get(family),
                    'observed_ed_band': [200, 299],
                }
                if family != 'hamm'
                else {
                    'path': 'guides/pricing.html#s2-yellow',
                    'kind': 'guide_pattern',
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


def market_equipment_patterns(add):
    """Reviewed SC/NL equipment combinations; heterogeneous extras stay unpriced."""
    patterns = [
        (
            'boot',
            'rare',
            '20 FRW + three resistances',
            stats(**{'480': 20}),
            counted(3, *(stats(**{prop: 20}) for prop in RESISTS)),
            23,
        ),
        ('belt', 'rare', '24 FHR + life + strength', stats(**{'430': 24, '418': 40, '437': 15}), None, 5),
        (
            'belt',
            'crafted',
            'Blood belt: 24 FHR + life + 10 open wounds + leech',
            stats(**{'430': 24, '418': 40, '566': 10, '462': 1}),
            None,
            4,
        ),
        (
            'glov',
            'rare',
            '+2 Passive and Magic skills + 20 IAS + attribute or resistance',
            stats(**{'455': 2, '457': 20}),
            counted(1, stats(**{'437': 15}), stats(**{'429': 15}), resist(20)),
            12,
        ),
    ]
    evidence_examples = {
        ('boot', 'rare'): ['1002422783093', '1002355993308', '1002342705143'],
        ('belt', 'rare'): ['1002255459224', '1002348777356', '1002487337128'],
        ('belt', 'crafted'): ['3560328050', '1255750539', '1002446630637'],
        ('glov', 'rare'): ['1121080165', '87687217', '1002381300750'],
    }
    for family, rarity, label, required, support, sellers in patterns:
        add(
            family,
            rarity,
            label,
            required,
            support,
            relax_support=False,
            source={
                'path': 'pricing/raw/traderie/',
                'reviewed_at': '2026-10-06',
                'scope': 'SC/NL/PC/RotW',
                'kind': 'paid_pattern',
                'independent_sellers': sellers,
                'guide': 'guides/pricing.html#s2-yellow; guides/pricing-primer.html#s6-1',
                'sample': 'cached priced misses; one seller vote across September and October pulls',
                'example_listing_ids': evidence_examples[family, rarity],
            },
        )


def affixed_rules():
    rows = []

    def add(
        family, rarity, label, required, support=None, source=SOURCE, low_rolls=None, labels=None, relax_support=True
    ):
        rows.append(
            {
                'family': family,
                'category': rarity,
                **required,
                **(support or {}),
                'pattern': {
                    **(support_pattern(support or {}) if relax_support else support or {}),
                    'properties': required.get('properties', {}) | (low_rolls or {}),
                },
                **({'labels': labels} if labels else {}),
                'pattern_label': label,
                'source': source,
                'imported_affixed_rule': True,
            }
        )

    add(
        'belt',
        'rare',
        'FHR belt: life and two substantial resistances',
        stats(**{'430': 24, '418': 40}),
        counted(2, *(stats(**{prop: 25}) for prop in RESISTS)),
        relax_support=False,
        source={
            'guide': 'guides/pricing-primer.html#miss rare belt',
            'reviewed_at': '2026-10-06',
            'scope': 'SC/NL/PC/RotW',
            'kind': 'review_pattern',
            'independent_sellers': 7,
            'without_strength_examples': ['1002165796238', '2912838208'],
            'threshold_basis': 'existing FHR/life and substantial-resistance review floors; no numeric price',
        },
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
            'Caster amulet: class skills + FCR + strong resistance, life or teleport',
            stats(**{skill: 2, '520': 10}),
            counted(1, resist(15), stats(**{'418': 40}), stats(**{'526': 1})),
            source='guides/pricing-primer.html#s6-1 RR-caster-amulet',
            relax_support=False,
        )
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
            'Rare circlet: +2 class skills and 20 faster cast rate',
            stats(**{skill: 2, '520': 20}),
            source='guides/pricing-primer.html#s3-3 (rare 2/20 circlets)',
        )
    for skill in ('454', '456', '410', '455'):
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
        if skill == '455':
            # Rare Passive gloves still need the independently reviewed extra affix.
            continue
        add(
            'glov',
            'rare',
            'Rare skill gloves: +2 skill tree and 20 increased attack speed',
            stats(**{skill: 2, '457': 20}),
            source='guides/pricing-primer.html#s3-3 (rare 2/20 skill gloves)',
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
    add(
        'ring',
        'crafted',
        'Blood ring: leech + strength + life + resistance',
        stats(**{'462': 1, '437': 10, '418': 30}),
        resist(10),
        relax_support=False,
        source={
            'guide': 'guides/pricing-primer.html#s6-1 CR-blood-ring',
            'path': 'pricing/raw/traderie/pull-20261003/3658180761-p0.json; pull-20261004/3658180761-p0.json',
            'reviewed_at': '2026-10-06',
            'scope': 'SC/NL/PC/RotW',
            'independent_sellers': 3,
            'threshold_basis': 'existing melee-ring strength/life/resistance floors; Blood recipe leech minimum',
        },
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
    for rarity in ('magic', 'rare'):
        add(
            'jewl',
            rarity,
            'Low-level damage jewel: 11+ maximum damage, equip level <=40',
            {'properties': {'448': {'min': 11}, '796': {'min': 1, 'max': 40}}},
            source='guides/pricing-primer.html#s3-2 JW-lowreq; Carnage and documented 11/12/15-max examples',
        )
    market_equipment_patterns(add)
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
