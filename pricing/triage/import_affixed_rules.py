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
    # Not covered by the 30 FRW circlet gate: its low rolls keep a 20 / 20 Tiara as a near miss.
    add(
        'circ',
        'magic',
        'Tiara: faster run/walk + all resistances',
        {**stats(**{'480': 30, '441': 30}), 'conditions': {'base_name': 'Tiara'}},
        low_rolls={'480': {'min': 1}, '441': {'min': 1}},
        labels={'480': 'faster run/walk', '441': 'all resistances'},
        source='guides/pindle-anya.html#s5 (30 FRW + 30 all resistances)',
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

    # Scoped 2026-10-08 cache, one vote per seller: enhanced damage is the gate.
    # Under half of the priced sellers list attack speed, a durability remedy or
    # both level-scaling stats, and normal/exceptional bases are listed alongside
    # elite ones (rares can be upgraded). Review candidates, never a price.
    def source(sellers, lowest):
        return {
            'path': 'pricing/data/appraisal-market.jsonl',
            'guide': 'guides/pricing.html#s2-yellow',
            'reviewed_at': '2026-10-08',
            'scope': 'SC/NL/PC/RotW',
            'kind': 'paid_pattern',
            'priced_sellers': sellers,
            'lowest_ask_ist': lowest,
        }

    # family: (priced sellers at or above the gate, their lowest ask in Ist)
    ethereal = {
        'swor': (84, 9.3),
        'axe': (59, 5.9),
        'mace': (33, 11.4),
        'hamm': (22, 11.4),
        'club': (21, 11.4),
        'scep': (19, 57.1),
        'h2h': (34, 5.9),
        'h2h2': (34, 22.8),
        'spea': (6, 45.7),
        'pole': (6, 34.3),
        'jave': (60, 4.1),
        'ajav': (15, 11.4),
        'taxe': (20, 11.4),
        'tkni': (14, 22.8),
    }
    # Bows cannot be ethereal; Amazon javelins and class claws are also listed
    # non-ethereal. Crossbows below 300% have three priced sellers at 1 Ist.
    plain = {
        'bow': (200, 69, 4.1),
        'abow': (200, 24, 5.9),
        'xbow': (300, 18, 9.3),
        'ajav': (200, 21, 1.0),
        'h2h2': (200, 6, 22.8),
    }
    gates = [(family, True, 200, evidence) for family, evidence in ethereal.items()]
    gates += [(family, False, damage, evidence) for family, (damage, *evidence) in plain.items()]
    for family, is_ethereal, damage, evidence in gates:
        for elite in (True, False):
            bases = sorted(
                b['name']
                for b in metadata()['bases'].values()
                if b['type'] == family and (base_tier(b['code']) == 'Elite') == elite
            )
            if not bases:
                continue
            add(
                family,
                'rare',
                'Physical weapon: '
                + ('ethereal, ' if is_ethereal else '')
                + f'{damage}%+ enhanced damage'
                + ('' if elite else '; review upgrade costs'),
                {**stats(**{'510': damage}), 'conditions': {'ethereal': is_ethereal, 'base_name': {'in': bases}}},
                labels={'510': 'enhanced damage'},
                source=source(*evidence),
            )
    # Phase Blades are intrinsically indestructible, so non-ethereal copies keep
    # the 2026-10-03/04 reviewed gates: speed, and Fool's scaling below 300%.
    phase_blade = {'base_name': 'Phase Blade', 'ethereal': False}
    for label, required in (
        ('Phase Blade: damage + speed', {'510': 300, '457': 30}),
        ("Phase Blade: Fool's scaling + damage + speed", {'510': 200, '457': 30, '535': 1, '536': 1}),
    ):
        add(
            'swor',
            'rare',
            label,
            {**stats(**required), 'conditions': phase_blade},
            source={
                'path': 'pricing/raw/traderie/pull-20261003/',
                'reviewed_at': '2026-10-04',
                'scope': 'SC/NL/PC/RotW',
                'kind': 'paid_pattern',
            },
        )


def belt_patterns(add):
    # Ethereal self-repairing gloves, boots and belts are listed by 12, 5 and 13
    # priced sellers, but assessment.ethereal_use prices those slots as
    # non-ethereal before rules run, so no ethereal pattern is added for them.
    # Scoped 2026-10-08 cache, one vote per seller. Recovery is the gate and
    # needs one companion roll; life is a companion, not a second gate.
    def source(sellers, lowest, own_drops):
        return {
            'path': 'pricing/data/appraisal-market.jsonl',
            'guide': 'guides/pricing.html#s2-yellow',
            'reviewed_at': '2026-10-08',
            'scope': 'SC/NL/PC/RotW',
            'kind': 'paid_pattern',
            'priced_sellers': sellers,
            'lowest_ask_ist': lowest,
            'own_drops_matched': own_drops,
        }

    add(
        'belt',
        'rare',
        '24 FHR belt + strength, life or a resistance',
        stats(**{'430': 24}),
        counted(1, stats(**{'437': 15}), stats(**{'418': 30}), resist(20)),
        relax_support=False,
        source=source(71, 0.1, '2 of 38'),
    )
    add(
        'belt',
        'rare',
        '17 FHR belt + life or strength',
        stats(**{'430': 17}),
        counted(1, stats(**{'418': 40}), stats(**{'437': 20})),
        relax_support=False,
        source=source(20, 1.0, '0 of 38'),
    )
    add(
        'belt',
        'rare',
        'Strength belt + a resistance',
        stats(**{'437': 25}),
        resist(20),
        relax_support=False,
        source=source(8, 1.0, '0 of 38'),
    )


def market_source(sellers, lowest, own_drops):
    """Scoped 2026-10-08 cache, one vote per seller; own_drops is the match rate among stored captures."""
    return {
        'path': 'pricing/data/appraisal-market.jsonl',
        'guide': 'guides/pricing.html#s2-yellow',
        'reviewed_at': '2026-10-08',
        'scope': 'SC/NL/PC/RotW',
        'kind': 'paid_pattern',
        'priced_sellers': sellers,
        'lowest_ask_ist': lowest,
        'own_drops_matched': own_drops,
    }


def glove_patterns(add):
    # A skill prefix is not required: 20 IAS with two useful companions is
    # listed by 38 priced sellers (lower quartile 11 Ist). One companion is not
    # enough: its lower quartile is 1 Ist and it matches ordinary drops.
    companions = [
        *(stats(**{prop: 20}) for prop in RESISTS),
        stats(**{'462': 3}),
        stats(**{'463': 3}),
        stats(**{'437': 15}),
        stats(**{'429': 15}),
        stats(**{'461': 15}),
    ]
    add(
        'glov',
        'rare',
        '20 IAS gloves + two of resistance, leech, strength, dexterity or magic find',
        stats(**{'457': 20}),
        counted(2, *companions),
        relax_support=False,
        source=market_source(38, 0.2, '0 of 60'),
    )
    add(
        'glov',
        'rare',
        '+2 Passive and Magic skills + 10 IAS',
        stats(**{'455': 2, '457': 10}),
        source=market_source(6, 11.4, '0 of 60'),
    )


SHIELD_SUFFIXES = ('418', '419', '420', '430')


def socketed_magic_patterns(add):
    # Sockets plus a suffix are the gate on magic armor: sellers list every base
    # tier, but none lists a bare four-socket body armor or shield (0 of 249 and
    # 0 of 74 listings). Three-socket helms need life (plain ones ask under 1 Ist).
    add(
        'tors',
        'magic',
        'Magic body armor: four sockets + a life, FHR, mana, dexterity, strength or damage-reduction suffix',
        {'conditions': {'sockets': 4}},
        counted(1, *(stats(**{prop: 1}) for prop in ('418', '430', '419', '429', '437', '435'))),
        source=market_source(63, 0.7, '0 of 4'),
    )
    add(
        'shie',
        'magic',
        'Magic shield: four sockets + a Deflecting, life, mana, energy or FHR suffix',
        {'conditions': {'sockets': 4}},
        counted(1, stats(**{'446': 20}), *(stats(**{prop: 1}) for prop in SHIELD_SUFFIXES)),
        source=market_source(17, 9.3, '0 of 4'),
    )
    for sockets, sellers, lowest in ((3, 20, 2.6), (2, 4, 5.9)):
        add(
            'shie',
            'magic',
            f'Magic shield of Deflecting: {sockets} sockets',
            {**stats(**{'446': 20}), 'conditions': {'sockets': sockets}},
            source=market_source(sellers, lowest, '0 of 4'),
        )
    add(
        'helm',
        'magic',
        'Magic helm: three sockets + life',
        {**stats(**{'418': 30}), 'conditions': {'sockets': 3}},
        source=market_source(12, 0.8, '0 of 2'),
    )
    for label, required, sellers, lowest in (
        ('Ethereal self-repairing magic helm', {**stats(**{'431': 1}), 'conditions': {'ethereal': True}}, 8, 11.4),
        ('Ethereal magic helm: two sockets', {'conditions': {'ethereal': True, 'sockets': 2}}, 6, 34.3),
    ):
        add('helm', 'magic', label, required, source=market_source(sellers, lowest, '0 of 2'))
    add(
        'tors',
        'magic',
        'Ethereal magic body armor: two sockets',
        {'conditions': {'ethereal': True, 'sockets': 2}},
        source=market_source(3, 171.3, '0 of 4'),
    )


def circlet_and_boot_patterns(add):
    from pricing.triage.import_class_rules import skill_prefixes

    trees = [prop for kinds in skill_prefixes().values() for prop in kinds['tree']] + ['1546', '1547', '1548']
    # Rare circlets: the class prefix alone is listed by 33 priced sellers the
    # older FCR-centred rules missed; trees and +1 class still need 20 FCR.
    for prop in CLASS_SKILLS:
        add(
            'circ', 'rare', 'Rare circlet: +2 class skills', stats(**{prop: 2}), source=market_source(33, 0.1, '0 of 9')
        )
        add(
            'circ',
            'rare',
            'Rare circlet: +1 class skills + 20 FCR',
            stats(**{prop: 1, '520': 20}),
            source=market_source(8, 11.4, '0 of 9'),
        )
    for prop in trees:
        add(
            'circ',
            'rare',
            'Rare circlet: +2 skill tree + 20 FCR',
            stats(**{prop: 2, '520': 20}),
            source=market_source(19, 0.3, '0 of 9'),
        )
    add(
        'circ',
        'rare',
        'Rare circlet: 30 FRW + 20 FCR',
        stats(**{'480': 30, '520': 20}),
        source=market_source(13, 11.4, '0 of 9'),
    )
    # Rare boots: high resistances carry them with reduced or no run speed.
    for label, required, count, sellers, lowest, own in (
        ('Rare boots: three resistances of 30+', {}, 3, 6, 9.3, '0 of 40'),
        ('Rare boots: 30 FRW + a resistance of 30+', stats(**{'480': 30}), 1, 6, 11.4, '1 of 40'),
        ('Rare boots: 20 FRW + two resistances of 30+', stats(**{'480': 20}), 2, 7, 9.3, '0 of 40'),
    ):
        add(
            'boot',
            'rare',
            label,
            required,
            counted(count, *(stats(**{prop: 30}) for prop in RESISTS)),
            relax_support=False,
            source=market_source(sellers, lowest, own),
        )


def remaining_type_patterns(add):
    """Scoped 2026-10-08 cache, one vote per seller: the types the earlier passes left on default vendor."""
    from pricing.triage.import_class_rules import skill_prefixes

    trees = [prop for kinds in skill_prefixes().values() for prop in kinds['tree']] + ['1546', '1547', '1548']
    ethereal = {'conditions': {'ethereal': True}}
    self_repair = {**stats(**{'431': 1}), **ethereal}
    two_sockets = {'conditions': {'sockets': {'min': 2}}}

    # Magic swords: +3 Warcries is the whole market (Call to Arms substitutes).
    for label, required, sellers, lowest in (
        ('Magic sword: +3 Warcries', stats(**{'406': 3}), 40, 0.2),
        ('Ethereal magic sword: 200+ enhanced damage', {**stats(**{'510': 200}), **ethereal}, 4, 11.4),
        ('Ethereal self-repairing magic sword', self_repair, 4, 11.4),
    ):
        add('swor', 'magic', label, required, source=market_source(sellers, lowest, '0 of 0'))
    # Rare helms, body armor and shields sell as mercenary or socket bases:
    # two sockets, or ethereal with self-repair. Plain ones ask under 1 Ist.
    for family, noun, socketed, repairing in (
        ('helm', 'helm', (26, 0.2), (18, 0.2)),
        ('tors', 'body armor', (21, 1.0), (16, 1.0)),
        ('shie', 'shield', (11, 4.1), (8, 13.7)),
        ('ashd', 'Paladin shield', (15, 1.0), (2, 114.2)),
    ):
        own = '0 of 3' if family == 'ashd' else '0 of 0'
        add(family, 'rare', f'Rare {noun}: two sockets', two_sockets, source=market_source(*socketed, own))
        add(family, 'rare', f'Ethereal self-repairing rare {noun}', self_repair, source=market_source(*repairing, own))
    add(
        'ashd',
        'rare',
        'Rare Paladin shield: 40+ all resistances',
        stats(**{'441': 40}),
        source=market_source(6, 0.8, '0 of 3'),
    )
    add(
        'ashd',
        'magic',
        'Magic Paladin shield: four sockets + a Deflecting, life, mana, energy or FHR suffix',
        {'conditions': {'sockets': 4}},
        counted(1, stats(**{'446': 20}), *(stats(**{prop: 1}) for prop in SHIELD_SUFFIXES)),
        source=market_source(11, 11.4, '0 of 6'),
    )
    # Rare javelins: ethereal ones are paid well below the 200 ED melee gate.
    for label, required, sellers, lowest in (
        (
            'Ethereal rare javelin: 120+ enhanced damage + 20 IAS',
            {**stats(**{'510': 120, '457': 20}), **ethereal},
            37,
            4.1,
        ),
        ('Ethereal rare javelin that replenishes quantity', {**stats(**{'563': 1}), **ethereal}, 24, 9.3),
        (
            'Non-ethereal rare javelin: 200+ enhanced damage',
            {**stats(**{'510': 200}), 'conditions': {'ethereal': False}},
            5,
            22.8,
        ),
    ):
        add('jave', 'rare', label, required, source=market_source(sellers, lowest, '0 of 0'))
    add(
        'staf',
        'rare',
        'Rare staff with Teleport charges',
        stats(**{'526': 1}),
        source=market_source(6, 22.8, '0 of 1'),
    )
    # Amulets. A skill roll needs company: bare +2 class asks 1 Ist and
    # matches two stored drops; with one companion the lowest ask is 11 Ist.
    amulet = [
        stats(**{'520': 10}),
        stats(**{'418': 40}),
        stats(**{'400': 60}),
        counted(1, stats(**{'441': 15}), *(stats(**{prop: 30}) for prop in RESISTS)),
        stats(**{'437': 20}),
        stats(**{'429': 15}),
        stats(**{'461': 20}),
        stats(**{'416': 4}),
        stats(**{'462': 5}),
        stats(**{'463': 5}),
    ]
    rolls = 'cast rate, life, mana, resistance, strength, dexterity, magic find, minimum damage or leech'
    for prop in CLASS_SKILLS:
        for rarity, sellers, lowest, own in (('rare', 16, 11.4, '0 of 20'), ('crafted', 31, 0.3, '0 of 0')):
            add(
                'amul',
                rarity,
                f'Amulet: +2 class skills + one of {rolls}',
                stats(**{prop: 2}),
                counted(1, *amulet),
                relax_support=False,
                source=market_source(sellers, lowest, own),
            )
        add(
            'amul',
            'rare',
            f'Amulet: +1 class skills + two of {rolls}',
            stats(**{prop: 1}),
            counted(2, *amulet),
            relax_support=False,
            source=market_source(11, 34.3, '0 of 20'),
        )
    magic_suffix = counted(
        1, stats(**{'520': 10}), stats(**{'418': 80}), stats(**{'437': 25}), stats(**{'429': 25}), stats(**{'461': 30})
    )
    # Cast rate stays with the reviewed caster trees in magic_patterns.
    circlet_suffix = counted(
        1,
        stats(**{'418': 80}),
        stats(**{'437': 25}),
        stats(**{'429': 25}),
        stats(**{'461': 30}),
        stats(**{'413': 20}),
    )
    for prop in trees:
        for rarity, sellers, lowest, own in (('rare', 17, 5.2, '0 of 20'), ('crafted', 7, 0.7, '0 of 0')):
            add(
                'amul',
                rarity,
                f'Amulet: +2 skill tree + two of {rolls}',
                stats(**{prop: 2}),
                counted(2, *amulet),
                relax_support=False,
                source=market_source(sellers, lowest, own),
            )
        add(
            'amul',
            'magic',
            'Magic amulet: +3 skill tree + cast rate, 80+ life, 25+ strength or dexterity, or 30+ magic find',
            stats(**{prop: 3}),
            magic_suffix,
            relax_support=False,
            source=market_source(14, 2.6, '0 of 82'),
        )
        add(
            'circ',
            'magic',
            'Magic circlet: +3 skill tree + 80+ life, 25+ strength or dexterity, 30+ MF or 20+ damage reduction',
            stats(**{prop: 3}),
            circlet_suffix,
            relax_support=False,
            source=market_source(6, 2.6, '0 of 15'),
        )
        add(
            'glov',
            'crafted',
            'Crafted gloves: +2 skill tree + 20 IAS',
            stats(**{prop: 2, '457': 20}),
            source=market_source(23, 1.0, '0 of 0'),
        )
    # Magic gloves below +3: only Javelin and Martial Arts are listed with
    # 20 IAS; no seller lists +2 Passive and Magic (guides/pricing.html §8).
    for prop, tree, sellers, lowest in (('456', 'Javelin and Spear', 9, 0.4), ('410', 'Martial Arts', 5, 1.0)):
        add(
            'glov',
            'magic',
            f'Magic gloves: +2 {tree} skills + 20 IAS',
            stats(**{prop: 2, '457': 20}),
            source=market_source(sellers, lowest, '0 of 69'),
        )
    add('circ', 'magic', 'Magic circlet: 30 FRW', stats(**{'480': 30}), source=market_source(7, 11.4, '0 of 15'))
    # Rare jewels: two useful rolls. None of 13 stored rare jewels has two.
    jewel = [
        stats(**{'510': 20}),
        stats(**{'448': 8}),
        stats(**{'416': 8}),
        stats(**{'437': 6}),
        stats(**{'429': 7}),
        stats(**{'441': 8}),
        *(stats(**{prop: 22}) for prop in RESISTS),
        stats(**{'430': 7}),
        stats(**{'457': 15}),
        stats(**{'418': 15}),
    ]
    add(
        'jewl',
        'rare',
        'Rare jewel: two of enhanced damage, flat damage, strength, dexterity, resistance, FHR, IAS or life',
        {},
        counted(2, *jewel),
        relax_support=False,
        source=market_source(28, 5.9, '0 of 13'),
    )
    # Crafted items: the recipe supplies part of the roll, so gates are looser
    # than the rare ones and every craft is looked at once anyway.
    add('belt', 'crafted', 'Crafted belt: 24 FHR', stats(**{'430': 24}), source=market_source(20, 5.9, '0 of 1'))
    add('belt', 'crafted', 'Crafted belt: 20+ strength', stats(**{'437': 20}), source=market_source(15, 9.8, '0 of 1'))
    ring = [
        stats(**{'437': 18}),
        stats(**{'429': 10}),
        stats(**{'418': 40}),
        stats(**{'400': 60}),
        stats(**{'416': 6}),
        counted(1, stats(**{'441': 8}), *(stats(**{prop: 25}) for prop in RESISTS)),
        stats(**{'462': 5}),
        stats(**{'463': 5}),
        stats(**{'520': 10}),
        stats(**{'417': 7}),
    ]
    add(
        'ring',
        'crafted',
        'Crafted ring: three of strength, dexterity, life, mana, minimum damage, resistance, leech, FCR or replenish',
        {},
        counted(3, *ring),
        relax_support=False,
        source=market_source(30, 5.9, '0 of 2'),
    )
    add(
        'ring',
        'crafted',
        'Crafted ring: 18+ strength + one more useful roll',
        stats(**{'437': 18}),
        counted(1, *ring[1:]),
        relax_support=False,
        source=market_source(10, 8.2, '0 of 2'),
    )
    glove = [
        *(stats(**{prop: 20}) for prop in RESISTS),
        stats(**{'462': 3}),
        stats(**{'463': 3}),
        stats(**{'437': 15}),
        stats(**{'429': 15}),
        stats(**{'461': 15}),
    ]
    add(
        'glov',
        'crafted',
        'Crafted gloves: 20 IAS + one of resistance, leech, strength, dexterity or magic find',
        stats(**{'457': 20}),
        counted(1, *glove),
        relax_support=False,
        source=market_source(17, 1.0, '0 of 0'),
    )
    add(
        'glov',
        'crafted',
        'Crafted gloves: two of resistance, leech, strength, dexterity or magic find',
        {},
        counted(2, *glove),
        relax_support=False,
        source=market_source(6, 22.8, '0 of 0'),
    )
    add(
        'boot',
        'crafted',
        'Crafted boots: 30 FRW + a 30+ resistance, 20+ magic find, 9+ dexterity or 10 FHR',
        stats(**{'480': 30}),
        counted(
            1,
            *(stats(**{prop: 30}) for prop in RESISTS),
            stats(**{'461': 20}),
            stats(**{'429': 9}),
            stats(**{'430': 10}),
        ),
        relax_support=False,
        source=market_source(24, 0.8, '0 of 0'),
    )
    add(
        'boot',
        'crafted',
        'Crafted boots: 20 FRW + two resistances of 30+',
        stats(**{'480': 20}),
        counted(2, *(stats(**{prop: 30}) for prop in RESISTS)),
        relax_support=False,
        source=market_source(4, 91.4, '0 of 0'),
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
    ]
    evidence_examples = {
        ('boot', 'rare'): ['1002422783093', '1002355993308', '1002342705143'],
        ('belt', 'rare'): ['1002255459224', '1002348777356', '1002487337128'],
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
        if rarity == 'crafted':
            # A crafted belt is already gated by 24 FHR alone.
            continue
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
    belt_patterns(add)
    glove_patterns(add)
    socketed_magic_patterns(add)
    circlet_and_boot_patterns(add)
    remaining_type_patterns(add)
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
