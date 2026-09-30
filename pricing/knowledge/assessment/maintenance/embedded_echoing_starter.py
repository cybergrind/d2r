"""Exact starter armor references with blank visible labels and native recipes."""

import json

from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


GUIDE = 'pricing/raw/mr/guides__echoing-strike-warlock-guide.html'
CONTEXTS = {
    2: ('Treachery', 'xtp', 'tors', 'Body Armor', {'93:0', '201:17103', '99:0', '43:0'}),
    3: ('Bulwark', 'crn', 'helm', 'Helmet', {'60:0', '36:0', '76:0', '99:0'}),
}


def validate_echoing_starter(review, resolved, role, root):
    evidence = review['evidence']
    context = CONTEXTS.get(resolved['context']['span_index'])
    if context is None or evidence['guide']['path'] != GUIDE:
        raise ValueError('Echoing starter reference outside reviewed context')
    word, base, kind, slot, priorities = context
    section = section_inventory(_read_pin(evidence['guide'], root))['sections'][13]
    if (
        evidence['reference']['section_locator'] != '/sections/13'
        or resolved['context']['side'] != 'merc'
        or section['heading'] != 'Mercenary'
        or 'Act 2 Blessed Aim Mercenary' not in section['text']
        or role.get('id') != f'echoing-strike-warlock-guide-0-merc-{word.lower()}-native'
        or role.get('build') != 'echoing-strike-warlock-guide'
        or role.get('variant') != 'Starter'
        or role.get('side') != 'merc'
        or role.get('slot') != slot
        or role.get('names') != [word]
        or role.get('types') != [kind]
        or set(role.get('qualities', [])) != {'normal', 'superior', 'low_quality'}
        or set(role.get('important_stats', [])) != priorities
        or role['source']['path'] != 'pricing/data/wp-a-builds.json'
        or role['source']['locator'] != '/echoing-strike-warlock-guide/variants/0'
    ):
        raise ValueError('Echoing starter wearer, source or contribution differs')
    pin = review['recipe_source']
    if pin['path'] != 'third-parties/d2data/json/runes.json' or {**pin, 'locator': '/' + word} not in role[
        'source'
    ].get('corroborating', []):
        raise ValueError('Echoing starter native source differs')
    recipe = json.loads(_read_pin(pin, root))[word]
    claims = (
        {'T1Code2': 'gethit-skill', 'T1Param2': 'Fade', 'T1Min2': 5, 'T1Max2': 15}
        if word == 'Treachery'
        else {'T1Code5': 'lifesteal', 'T1Min5': 4, 'T1Max5': 6, 'T1Code3': 'red-dmg%', 'T1Min3': 10, 'T1Max3': 15}
    )
    if any(recipe.get(k) != v for k, v in claims.items()):
        raise ValueError('Echoing starter native trigger or Non-Ladder rolls differ')
    item = resolved['item']
    if (
        item.get('base') != base
        or item.get('quality') != 7
        or item.get('ethereal') is not True
        or item.get('sockets') != 3
        or item.get('socketedItems') != [recipe[f'Rune{i}'] for i in range(1, 4)]
    ):
        raise ValueError('Echoing starter native recipe/base/socket example differs')
    required = [('context_eq', 'player_class', 'Warlock'), ('context_eq', 'mercenary_type', 'Act 2 Blessed Aim')]
    required += [
        ('fact_eq', k, v)
        for k, v in [
            ('identified', True),
            ('base_code', base),
            ('ethereal', True),
            ('runeword', word),
            ('sockets', 3),
            ('socket_contents', 'filled'),
        ]
    ]
    if not all(requires_eq(role.get('must', {}), *claim) for claim in required):
        raise ValueError('Echoing starter applicability requirements differ')
