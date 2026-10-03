"""Transcribe guide class-item combinations as reloadable, price-free patterns."""

import json

from pricing.knowledge.refresh import atomic_json
from pricing.triage.build import ROOT


SOURCE = 'guides/pricing.html §2 blue/yellow and §7; PLAN.md §3.8'


def class_rules():
    rows = []

    def add(family, category, label, properties, conditions=None):
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
                'conditions': conditions,
                'pattern': {'properties': {p: {'min': v} for p, v in properties.items()}},
                'pattern_label': label,
                'source': SOURCE,
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
            {'453': 2, '454': 3 if category == 'magic' else 2, '457': 40 if category == 'magic' else 30},
        )
    for tree in ('1546', '1547', '1548'):
        add('grim', 'magic', 'Warlock tree + all resistances', {tree: 3, '441': 1})
    return rows


def main():
    path = ROOT / 'pricing/data/triage/rules.json'
    document = json.loads(path.read_text())
    rows = class_rules()
    document['rows'] = [r for r in document['rows'] if not r.get('imported_class_rule')] + rows
    atomic_json(path, document)
    print(json.dumps({'class_rules': len(rows), 'numeric_prices_added': 0, 'new_types_enabled': 0}))


if __name__ == '__main__':
    main()
