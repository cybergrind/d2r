"""Transcribe guide class-item combinations as reloadable, price-free patterns."""

import json

from pricing.knowledge.refresh import atomic_json
from pricing.triage.build import ROOT


SOURCE = 'guides/pricing.html §2 blue/yellow and §7; PLAN.md §3.8'


CLASS_ITEMS = {
    'phlm': 'Barbarian',
    'pelt': 'Druid',
    'head': 'Necromancer',
    'wand': 'Necromancer',
    'orb': 'Sorceress',
    'ashd': 'Paladin',
    'scep': 'Paladin',
    'h2h': 'Assassin',
    'h2h2': 'Assassin',
    'ajav': 'Amazon',
}


TREES = {
    'Barbarian': ('Combat Skills', 'Masteries', 'Warcries'),
    'Druid': ('Summoning Skills', 'Shape Shifting Skills', 'Elemental Skills'),
    'Necromancer': ('Curses', 'Poison and Bone Skills', 'Summoning Skills'),
    'Sorceress': ('Fire Skills', 'Lightning Skills', 'Cold Skills'),
    'Paladin': ('Combat Skills', 'Offensive Auras', 'Defensive Auras'),
    'Assassin': ('Traps', 'Shadow Disciplines', 'Martial Arts'),
    'Amazon': ('Bow and Crossbow Skills', 'Passive and Magic Skills', 'Javelin and Spear Skills'),
}


# Skills that are the best skill on the +5 listings of two or more priced
# sellers, by the skill's tree (scoped 2026-10-08 cache).
PAID_SKILLS = {
    'phlm': {
        'Warcries': ('Battle Orders', 'Battle Command', 'War Cry', 'Grim Ward'),
        'Masteries': ('Increased Speed',),
    },
    'pelt': {
        'Elemental Skills': ('Tornado', 'Armageddon', 'Hurricane', 'Volcano'),
        'Summoning Skills': ('Summon Grizzly',),
        'Shape Shifting Skills': ('Fury', 'Shock Wave', 'Fire Claws'),
    },
    'head': {'Poison and Bone Skills': ('Poison Nova', 'Bone Spirit', 'Bone Spear')},
    'wand': {'Poison and Bone Skills': ('Bone Spear', 'Poison Nova', 'Bone Spirit')},
    'orb': {
        'Lightning Skills': (
            'Chain Lightning',
            'Lightning',
            'Nova',
            'Lightning Mastery',
            'Thunder Storm',
            'Energy Shield',
        ),
        'Fire Skills': ('Enchant', 'Fire Ball', 'Hydra', 'Meteor', 'Fire Wall', 'Fire Mastery'),
        'Cold Skills': ('Blizzard', 'Frozen Orb', 'Cold Mastery'),
    },
    'scep': {'Combat Skills': ('Fist of the Heavens', 'Blessed Hammer')},
    'h2h2': {'Traps': ('Lightning Sentry',), 'Shadow Disciplines': ('Venom', 'Fade')},
}
# Priced sellers at +5 or more to one skill: (magic, rare).
PAID_SKILL_SELLERS = {
    'phlm': (34, 46),
    'pelt': (37, 40),
    'head': (51, 17),
    'wand': (19, 5),
    'orb': (91, 39),
    'scep': (13, 2),
    'h2h2': (34, 8),
}


def skill_prefixes():
    """Class-wide and skill-tree property ids by class, read from the market property labels."""
    properties = json.loads((ROOT / 'pricing/data/appraisal-properties.json').read_text())['properties']
    by_label = {(entry.get('labels') or [''])[0]: prop for prop, entry in properties.items()}
    return {
        owner: {
            'class': {by_label[f'+{{{{value}}}} to {owner} Skill Levels']: f'{owner} skills'},
            'tree': {by_label[f'+{{{{value}}}} to {tree} ({owner} Only)']: tree for tree in trees},
        }
        for owner, trees in TREES.items()
    }


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
        any_base=False,
    ):
        conditions = dict(conditions or {})
        if family == 'knif' and not any_base:
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

    # Scoped 2026-10-08 cache, one vote per seller. Warlock daggers and grimoires
    # are gated by the class or tree prefix. Casters list every dagger base, so
    # skill patterns are not base-restricted.
    warlock_source = {
        'path': 'pricing/data/appraisal-market.jsonl',
        'guide': 'guides/pricing.html#s7',
        'reviewed_at': '2026-10-08',
        'scope': 'SC/NL/PC/RotW',
        'kind': 'paid_pattern',
    }
    trees = {'1546': 'Demon Skills', '1547': 'Eldritch Skills', '1548': 'Chaos Skills'}
    for category, sellers, tree_level, tree_sellers in (('magic', 3, 3, 3), ('rare', 6, 2, 7)):
        add(
            'knif',
            category,
            'Warlock dagger: +2 Warlock skills',
            {'1862': 2},
            labels={'1862': 'Warlock skills'},
            source=warlock_source | {'priced_sellers': sellers},
            any_base=True,
        )
        for tree, label in trees.items():
            add(
                'knif',
                category,
                f'Warlock dagger: +{tree_level} {label}',
                {tree: tree_level},
                labels={tree: label},
                source=warlock_source | {'priced_sellers_across_trees': tree_sellers},
                any_base=True,
            )
        rows.append(
            {
                'family': 'knif',
                'category': category,
                'default_reason': (
                    'needs +2 Warlock, a full tree prefix or an ethereal high-damage roll; staffmods alone are not paid'
                ),
                'source': SOURCE,
                'imported_class_rule': True,
            }
        )
    add(
        'knif',
        'magic',
        'Echoing dagger: +3 Warcries for buff switch',
        {'406': 3},
        labels={'406': 'Warcries'},
        source=warlock_source | {'priced_sellers': 3},
        any_base=True,
    )
    # Thirty-one priced sellers ask at least 9 Ist for ethereal rare daggers with
    # 200%+ enhanced damage; under half of them list leech or attack speed.
    for ethereal, damage, sellers in ((True, 200, 31), (False, 300, 3)):
        add(
            'knif',
            'rare',
            'Physical dagger: ' + ('ethereal, ' if ethereal else '') + f'{damage}%+ enhanced damage',
            {'510': damage},
            {'ethereal': ethereal},
            labels={'510': 'enhanced damage'},
            source=warlock_source | {'priced_sellers': sellers},
            any_base=True,
        )
    paid_grimoire = ('1558', '1578', '1577', '1579', '1559', '1554', '1553')
    for category, sellers in (('magic', 7), ('rare', 40)):
        add(
            'grim',
            category,
            'Warlock grimoire: +2 Warlock skills',
            {'1862': 2},
            labels={'1862': 'Warlock skills'},
            source=warlock_source | {'priced_sellers': sellers},
        )
    for tree, label in trees.items():
        add(
            'grim',
            'rare',
            f'Warlock grimoire: +2 {label} with a +3 paid staffmod',
            {tree: 2},
            support={'count': 1, 'of': [{'properties': {skill: {'min': 3}}} for skill in paid_grimoire]},
            labels={tree: label},
            source=warlock_source | {'priced_sellers_across_trees': 6},
        )
    # Summed skill gate (scoped 2026-10-08 cache, reviewed 2026-10-09). A class
    # item is listed for one skill, so the prefix and the staffmod count only
    # together: +5 to a single paid skill from the class prefix or the skill's
    # own tree prefix plus the staffmod. Under +5 the pooled magic listings ask
    # a 10-Ist median against 69 at +5 and 91 at +6 and draw 3 offers on 84
    # listings. PAID_SKILLS holds the skills that are the best skill on the
    # listings of two or more priced sellers; a skill that only rides along on
    # a listing sold for another one is not in it.
    prefixes = skill_prefixes()
    properties = json.loads((ROOT / 'pricing/data/appraisal-properties.json').read_text())['properties']
    skill_ids = {(entry.get('labels') or [''])[0]: prop for prop, entry in properties.items()}
    summed_source = warlock_source | {'reviewed_at': '2026-10-09', 'guide': 'guides/pricing.html#s2-blue'}
    for family, sellers in PAID_SKILL_SELLERS.items():
        owner = CLASS_ITEMS[family]
        (class_prop,) = prefixes[owner]['class']
        tree_props = {label: prop for prop, label in prefixes[owner]['tree'].items()}
        paid = {
            tree: {skill_ids[f'+{{{{value}}}} to {skill} ({owner} Only)']: skill for skill in skills}
            for tree, skills in PAID_SKILLS[family].items()
        }
        every = {prop: skill for skills in paid.values() for prop, skill in skills.items()}
        for category, priced in zip(('magic', 'rare'), sellers, strict=True):
            source = summed_source | {'priced_sellers_at_five': priced}

            shapes = [(class_prop, f'{owner} skills', 2, every, 3)]
            for tree, skills in paid.items():
                shapes.append((tree_props[tree], tree, 2, skills, 3))
                if category == 'magic':
                    shapes.append((tree_props[tree], tree, 3, skills, 2))
            for prefix, label, level, skills, staffmod in shapes:
                add(
                    family,
                    category,
                    f'{owner} item: +{level + staffmod} to a paid skill (+{level} {label} and a +{staffmod} skill)',
                    {prefix: level},
                    support={'count': 1, 'of': [{'properties': {skill: {'min': staffmod}}} for skill in skills]},
                    labels={prefix: label} | skills,
                    source=source,
                )
    # These class items carry no staffmods, so their prefix is the whole skill roll.
    for family, category, minimum, sellers, lowest in (
        ('ashd', 'rare', 2, 15, 0.8),
        ('h2h', 'rare', 2, 6, 4.1),
        ('ajav', 'magic', 2, 7, 1.0),
    ):
        owner = CLASS_ITEMS[family]
        for prop, label in prefixes[owner]['class'].items():
            add(
                family,
                category,
                f'{owner} item: +{minimum} {label}',
                {prop: minimum},
                labels={prop: label},
                source=warlock_source | {'priced_sellers': sellers, 'lowest_ask_ist': lowest},
            )
    # Rare class items under +5 are still listed with two sockets: Barbarian
    # helms, pelts and elite-type claws draw offers as often as the skill route.
    for family, label, sellers, lowest in (
        ('phlm', 'Rare Barbarian helm: two sockets', 17, 11.4),
        ('pelt', 'Rare pelt: two sockets', 9, 11.4),
        ('h2h2', 'Rare claw: two sockets', 9, 22.8),
    ):
        add(
            family,
            'rare',
            label,
            {},
            {'sockets': {'min': 2}},
            source=warlock_source | {'priced_sellers': sellers, 'lowest_ask_ist': lowest},
        )
    add(
        'phlm',
        'rare',
        'Ethereal self-repairing Barbarian helm',
        {'431': 1},
        {'ethereal': True},
        source=warlock_source | {'priced_sellers': 11, 'lowest_ask_ist': 22.8},
    )
    for category in ('magic', 'rare'):
        add(
            'ajav',
            category,
            'Amazon + Javelin skills + attack speed',
            {'453': 2, '456': 3 if category == 'magic' else 2, '457': 40 if category == 'magic' else 30},
            bucket='amazon-class-javelin-speed' if category == 'magic' else None,
            low_rolls={'453': 1} if category == 'magic' else None,
            labels={'453': 'Amazon skills'},
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
    # The cached Fire Blast planner names the complete claw, including its staffmods.
    # Demand permits review; it supplies no Non-Ladder asking-price estimate.
    add(
        'h2h2',
        'magic',
        'Fire Blast claw: +3 Traps, +3 Fire Blast, +3 Weapon Block, 40 IAS and two sockets',
        {'408': 3, '1054': 3, '1065': 3, '457': 40},
        {'base_name': 'Greater Claws', 'ethereal': False, 'sockets': 2},
        source={
            'path': 'pricing/raw/mr/planners/e113x0l4.json',
            'locator': 'planner.items.49 and 56',
            'source_date': '2026-02-17',
            'reviewed_at': '2026-10-06',
            'kind': 'build_demand',
        },
    )
    # Fool's scaling damage with 200% ED and 30 IAS is the one claw pattern the
    # enhanced-damage gates miss: a non-ethereal claw below the elite types.
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

    # Guide-named "of the Magus" orb: class skills with 20 FCR, with or without a staffmod.
    for category in ('magic', 'rare'):
        add('orb', category, 'Sorceress skills + 20 faster cast rate', {'514': 2, '520': 20})
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
            }
        )
    )


if __name__ == '__main__':
    main()
