"""Guide §2 jewelry and wearable combinations, without invented numerical prices."""

import json

from pricing.knowledge.refresh import atomic_json
from pricing.triage.build import ROOT


SOURCE = 'guides/pricing.html §2 blue/yellow/orange'
CLASS_SKILLS = ('453', '514', '498', '442', '403', '488', '519', '1862')
RESISTS = ('427', '428', '426', '401')


def stats(**values):
    return {'properties': {key: {'min': value} for key, value in values.items()}}


def counted(count, *options):
    return {'at_least': {'count': count, 'of': list(options)}}


def resist(value):
    return counted(1, *(stats(**{prop: value}) for prop in RESISTS))


def affixed_rules():
    rows = []

    def add(family, rarity, label, required, support=None):
        rows.append(
            {
                'family': family,
                'category': rarity,
                **required,
                **(support or {}),
                'pattern': {'properties': required.get('properties', {})},
                'pattern_label': label,
                'source': SOURCE,
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
            counted(2, resist(15), stats(**{'418': 40}), stats(**{'437': 1}), stats(**{'429': 1})),
        )
        add('amul', 'crafted', 'Caster craft: class skills + 20 FCR', stats(**{skill: 2, '520': 20}))
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
                stats(**{'437': 1}),
                stats(**{'429': 1}),
            ),
        )
    for skill in ('454', '456', '410'):
        add('glov', 'magic', 'Skill gloves + 20 IAS', stats(**{skill: 3, '457': 20}))
        add(
            'glov',
            'rare',
            'Rare skill gloves + 20 IAS + two supporting affixes',
            stats(**{skill: 2, '457': 20}),
            counted(2, stats(**{'437': 1}), stats(**{'429': 1}), stats(**{'418': 1}), resist(1)),
        )
    add(
        'boot',
        'rare',
        'Fast boots + two high resistances',
        stats(**{'480': 30}),
        counted(2, *(stats(**{prop: 25}) for prop in RESISTS)),
    )
    add(
        'belt',
        'rare',
        'FHR belt + life + strength and resistance',
        stats(**{'430': 24, '418': 40}),
        counted(2, resist(1), stats(**{'437': 1})),
    )
    add(
        'glov',
        'crafted',
        'Blood gloves: leech + crushing blow + life + speed or skills',
        stats(**{'462': 1, '567': 5, '418': 1}),
        counted(1, stats(**{'457': 20}), *(stats(**{p: 2}) for p in ('454', '456', '410'))),
    )
    return rows


def main():
    path = ROOT / 'pricing/data/triage/rules.json'
    document = json.loads(path.read_text())
    rows = affixed_rules()
    document['rows'] = [r for r in document['rows'] if not r.get('imported_affixed_rule')] + rows
    atomic_json(path, document)
    print(json.dumps({'affixed_rules': len(rows), 'numeric_prices_added': 0, 'new_types_enabled': 0}))


if __name__ == '__main__':
    main()
