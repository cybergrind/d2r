"""Transcribe guide class-item combinations as reloadable, price-free patterns."""

import json

from pricing.knowledge.refresh import atomic_json
from pricing.triage.build import ROOT


SOURCE = 'guides/pricing.html §2 blue/yellow and §7; PLAN.md §3.8'


def class_rules():
    rows = []

    def add(
        family,
        category,
        label,
        properties,
        conditions=None,
        support=None,
        source=SOURCE,
        low_rolls=None,
        labels=None,
        bucket=None,
    ):
        conditions = dict(conditions or {})
        if family == 'knif':
            conditions['base_name'] = {
                'in': [
                    'Blade',
                    'Stilleto',
                    'Legend Spike',
                    'Kriss',
                    'Cinquedeas',
                    'Fanged Knife',
                    'Bone Knife',
                    'Mithral Point',
                ]
            }
        rows.append(
            {
                'family': family,
                'category': category,
                'properties': {p: {'min': value} for p, value in properties.items()},
                **(
                    {
                        'bucket': bucket,
                        'band_facets': ['base_code', 'ethereal', 'sockets', 'socket_contents', 'base_modifiers'],
                    }
                    if bucket
                    else {}
                ),
                'conditions': conditions,
                **({'at_least': support} if support else {}),
                'pattern': {'properties': {p: {'min': v} for p, v in (properties | (low_rolls or {})).items()}},
                **({'labels': labels} if labels else {}),
                'pattern_label': label,
                'source': source,
                'imported_class_rule': True,
            }
        )

    for category in ('magic', 'rare'):
        # PLAN §3.8 explicitly requires the class-skill gate; guide §7 supplies paid staffmods.
        for skill in ('1565', '1579', '1561'):
            supports = (
                ({'457': 20},)
                if category == 'magic'
                else ({'448': 1}, {'418': 1}, {'427': 1}, {'428': 1}, {'426': 1}, {'401': 1})
            )
            for support in supports:
                add(
                    'knif',
                    category,
                    'Warlock class skills + paid staffmod + supporting affix',
                    {'1862': 2, skill: 3, **support},
                )
            if category == 'rare':
                add(
                    'knif',
                    category,
                    'Warlock class skills + paid staffmod + socket',
                    {'1862': 2, skill: 3},
                    {'sockets': {'min': 1}},
                )
        rows.append(
            {
                'family': 'knif',
                'category': category,
                'default_reason': (
                    'needs +2 Warlock, a paid staffmod and supporting affix; staffmods alone are not paid'
                ),
                'source': SOURCE,
                'imported_class_rule': True,
            }
        )
        # +2 class / +3 Battle Orders is specifically priced in the guide.
        add('phlm', category, 'Barbarian skills + Battle Orders switch helm', {'403': 2, '765': 3})
        if category == 'magic':
            add('phlm', category, 'Warcries + Battle Orders switch helm', {'406': 3, '765': 3})
        for skill in ('1024', '756'):
            for support in ({'449': 1}, {'446': 1}):
                add('head', category, 'Necromancer skills + paid staffmod + blocking', {'498': 2, skill: 3, **support})
            add('head', category, 'Necromancer skills + paid staffmod + sockets', {'498': 2, skill: 3}, {'sockets': 2})
        add('orb', category, 'Sorceress skills + 20 faster cast rate', {'514': 2, '520': 20})
        for support in ({'418': 1}, {'441': 1}, {'520': 1}):
            add('grim', category, 'Warlock grimoire class skills + supporting affix', {'1862': 2, **support})
        add('grim', category, 'Warlock grimoire class skills + two sockets', {'1862': 2}, {'sockets': 2})
        for family in ('h2h', 'h2h2'):
            for skill in ('1073', '1116', '1077'):
                for prefix in ({'519': 2}, {'408': 3}):
                    add(
                        family,
                        category,
                        'Assassin skills + trap staffmod + attack speed',
                        {**prefix, skill: 3, '457': 40},
                    )
        add(
            'ajav',
            category,
            'Amazon + Javelin skills + attack speed',
            {'453': 2, '456': 3 if category == 'magic' else 2, '457': 40 if category == 'magic' else 30},
            bucket='amazon-class-javelin-speed' if category == 'magic' else None,
        )
    for prefix in ({'519': 2}, {'408': 3}):
        add(
            'h2h2',
            'magic',
            'Trap claw: skill prefix + 3 Lightning Sentry + two sockets',
            prefix | {'1073': 3},
            {'sockets': 2},
            source={
                'path': 'pricing/raw/traderie/pull-20261003/',
                'reviewed_at': '2026-10-04',
                'scope': 'SC/NL/PC/RotW',
                'kind': 'paid_pattern',
                'independent_sellers': 9,
                'guide': 'guides/pricing.html §2 blue class items',
            },
        )
    # Lancer's prefix stacks with native Amazon javelin skills; +2 Amazon is
    # an alternative prefix, not a prerequisite for the 6/40 combination.
    for low_rolls, sellers in (({'456': 5}, 7), ({'457': 30}, 4)):
        add(
            'ajav',
            'magic',
            'Stacked Javelin skills + attack speed',
            {'456': 6, '457': 40},
            low_rolls=low_rolls,
            labels={'456': 'Javelin skills', '457': 'increased attack speed'},
            source={
                'path': 'pricing/raw/traderie/pull-20261003/',
                'reviewed_at': '2026-10-03',
                'scope': 'SC/NL/PC/RotW',
                'kind': 'paid_pattern',
                'top_pattern_sellers': 3,
                'lower_pattern_sellers': sellers,
                'lower_pattern': low_rolls,
            },
        )
    for skills, speed in ((6, 40), (5, 40), (6, 30)):
        rows.append(
            {
                'family': 'ajav',
                'category': 'magic',
                'bucket': f'magic-javelin-{skills}-{speed}',
                'properties': {'456': skills, '457': speed},
                'band_facets': ['base_code', 'ethereal', 'base_modifiers'],
                'source': 'pricing/raw/traderie/; scoped 2026-10-03 stacked javelin asks',
                'imported_class_rule': True,
            }
        )
    # Scoped scepter asks: four Combat-prefix sellers, two class-prefix
    # sellers pair +3 Fist of the Heavens with Redemption or cast rate.
    for prefix, minimum in (('442', 2), ('443', 3)):
        for support, value in (('1047', 1), ('520', 10)):
            add(
                'scep',
                'magic',
                'Paladin skills + Fist of the Heavens + Redemption or cast rate',
                {prefix: minimum, '581': 3, support: value},
                labels={'581': 'Fist of the Heavens', '1047': 'Redemption', '520': 'faster cast rate'},
                source={
                    'path': 'pricing/raw/traderie/pull-20261003/',
                    'guide': 'guides/pricing.html §2 class-item combinations',
                    'reviewed_at': '2026-10-03',
                    'scope': 'SC/NL/PC/RotW',
                    'kind': 'paid_pattern',
                    'prefix': prefix,
                    'support': support,
                },
            )
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.mechanics.base_tiers import base_tier

    for family in ('h2h', 'h2h2'):
        for needs_upgrade in (False, True):
            claw_bases = sorted(
                b['name']
                for b in metadata()['bases'].values()
                if b['type'] == family and b['max_sockets'] >= 1 and (base_tier(b['code']) != 'Elite') == needs_upgrade
            )
            if not claw_bases:
                continue
            for ethereal in (False, True):
                for proven_repair in (False, True) if ethereal else (False,):
                    reviews = []
                    if needs_upgrade:
                        reviews.append('upgrade')
                    if ethereal and not proven_repair:
                        reviews.append('repair/Zod')
                    label = "Fool's physical claw: damage + speed"
                    if reviews:
                        label += '; review ' + ' and '.join(reviews) + ' costs'
                    add(
                        family,
                        'rare',
                        label,
                        {'510': 200, '457': 30, '535': 1, '536': 1},
                        {'base_name': {'in': claw_bases}, 'ethereal': ethereal},
                        support={
                            'count': 1,
                            'of': [{'properties': {'431': {'min': 1}}}, {'properties': {'432': True}}],
                        }
                        if proven_repair
                        else None,
                        source={
                            'path': 'pricing/raw/traderie/pull-20261003/',
                            'reviewed_at': '2026-10-03',
                            'scope': 'SC/NL/PC/RotW',
                            'kind': 'paid_pattern',
                            'independent_sellers_across_claw_bases': 19,
                            'pricing': 'review only; base and durability costs are not priced',
                        },
                    )

    # Guide §2 yellow: elite Paladin shields need the class prefix, a
    # resistance/block-rate gate, and two further supporting rolls.
    paladin_bases = sorted(
        b['name'] for b in metadata()['bases'].values() if b['type'] == 'ashd' and base_tier(b['code']) == 'Elite'
    )
    for gate in ('441', '449'):
        supporting = [
            {'properties': {'430': {'min': 1}}},
            {'properties': {'418': {'min': 1}}},
            {'conditions': {'sockets': {'min': 1}}},
        ]
        if gate == '449':
            supporting.append({'properties': {'441': {'min': 1}}})
        add(
            'ashd',
            'rare',
            'Elite Paladin shield: class skills, resistance or block rate and two supporting rolls',
            {'442': 2, gate: 1},
            {'base_name': {'in': paladin_bases}},
            {'count': 2, 'of': supporting},
        )
    # Guide class-prefix/staffmod shape, checked against scoped 2026-10-03
    # cached asks: rare Tornado/Armageddon 20/5 independent sellers; magic
    # Elemental Tornado/Armageddon 9/6, Shapeshifting Fire Claws 3, Summon Grizzly 5.
    pelt_source = {
        'path': 'pricing/raw/traderie/pull-20261003/',
        'guide': 'guides/pricing.html#s2-yellow',
        'reviewed_at': '2026-10-03',
        'scope': 'SC/NL/PC/RotW',
        'kind': 'paid_pattern',
    }
    pelt_labels = {'972': 'Tornado', '976': 'Armageddon', '966': 'Fire Claws', '974': 'Summon Grizzly'}
    for spell in ('972', '976'):
        add(
            'pelt',
            'rare',
            'Druid skills + paid spell + two supporting rolls',
            {'488': 2, spell: 3},
            support={
                'count': 2,
                'of': [
                    {'properties': {'430': {'min': 1}}},
                    {'properties': {'418': {'min': 1}}},
                    {'conditions': {'sockets': {'min': 1}}},
                    {
                        'at_least': {
                            'count': 1,
                            'of': [{'properties': {prop: {'min': 1}}} for prop in ('427', '428', '426', '401')],
                        }
                    },
                ],
            },
            source=pelt_source | {'spell': spell, 'prefix': '488'},
            low_rolls={spell: 1},
            labels=pelt_labels,
        )
    for tree, spell in (('487', '972'), ('487', '976'), ('486', '966'), ('485', '974')):
        add(
            'pelt',
            'magic',
            'Druid tree + matching paid spell + two sockets',
            {tree: 3, spell: 3},
            {'sockets': 2},
            source=pelt_source | {'spell': spell, 'prefix': tree},
            low_rolls={spell: 1},
            labels=pelt_labels,
        )
    for tree in ('1546', '1547', '1548'):
        add('grim', 'magic', 'Warlock tree + all resistances', {tree: 3, '441': 1})
    for skill, minimum in (('453', 2), ('456', 3)):
        add(
            'aspe',
            'rare',
            'Amazon spear: damage, skills, speed, two sockets and two supporting mods',
            {'510': 200, skill: minimum, '457': 40},
            {'sockets': 2, 'base_name': {'in': ['Ceremonial Pike', 'Matriarchal Spear', 'Matriarchal Pike']}},
            {'count': 2, 'of': [{'properties': {p: {'min': 1}}} for p in ('462', '535', '437', '429')]},
        )
    add(
        'knif',
        'rare',
        'Ethereal melee dagger: speed, leech and supporting affix',
        {'457': 30, '462': 1},
        {'ethereal': True},
        {
            'count': 1,
            'of': [
                *[{'properties': {p: {'min': 1}}} for p in ('448', '418', '427', '428', '426', '401')],
                {'conditions': {'sockets': {'min': 1}}},
            ],
        },
    )
    # Scoped cached asks reviewed 2026-10-03: all six matching tree/spell pairs
    # have priced sellers with FCR or two sockets. This establishes the pattern,
    # not a price for an arbitrary orb with additional/missing secondary mods.
    orb_labels = {
        '944': 'Enchant',
        '602': 'Fire Ball',
        '948': 'Nova',
        '1049': 'Lightning',
        '598': 'Chain Lightning',
        '703': 'Blizzard',
    }
    for tree, spells in (('515', ('944', '602')), ('516', ('948', '1049', '598')), ('517', ('703',))):
        for spell in spells:
            for support in ('fcr', 'sockets'):
                add(
                    'orb',
                    'magic',
                    'Sorceress tree + matching spell + cast rate or two sockets',
                    {tree: 3, spell: 3, **({'520': 20} if support == 'fcr' else {})},
                    {'sockets': 2} if support == 'sockets' else None,
                    low_rolls={spell: 1},
                    labels=orb_labels,
                    source={
                        'path': 'pricing/raw/traderie/pull-20261003/',
                        'reviewed_at': '2026-10-03',
                        'scope': 'SC/NL/PC/RotW',
                        'kind': 'paid_pattern',
                        'query': {
                            'category': 'magic',
                            'family': 'orb',
                            'tree': tree,
                            'spell': spell,
                            'support': support,
                        },
                    },
                )
    return rows


def main():
    path = ROOT / 'pricing/data/triage/rules.json'
    document = json.loads(path.read_text())
    rows = class_rules()
    document['rows'] = [r for r in document['rows'] if not r.get('imported_class_rule')] + rows
    atomic_json(path, document)
    print(
        json.dumps(
            {
                'class_rules': len(rows),
                'price_patterns': sum(bool(r.get('bucket')) for r in rows),
                'new_types_enabled': 0,
            }
        )
    )


if __name__ == '__main__':
    main()
