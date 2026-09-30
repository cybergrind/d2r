"""Exact Malice example: mercenary Open Wounds within the documented Ubers setup."""

import json

from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


GUIDE = 'pricing/raw/mr/guides__echoing-strike-warlock-guide.html'
COMPANIONS = {"Sazabi's Cobalt Redeemer", "Sazabi's Ghost Liberator", "Sazabi's Mental Sheath"}


def validate_echoing_malice(review, resolved, role, root):
    evidence, context, item = review['evidence'], resolved['context'], resolved['item']
    if (
        evidence['guide']['path'] != GUIDE
        or evidence['reference']['section_locator'] != '/sections/25'
        or context['span_index'] != 14
        or context['label'] != 'Malice Mythical Sword'
        or context['side'] != 'merc'
        or role.get('id') != 'echoing-strike-warlock-guide-malice-ubers-source-recipe'
        or role.get('build') != 'echoing-strike-warlock-guide'
        or role.get('variant') != 'Ubers'
        or role.get('side') != 'merc'
        or role.get('slot') != 'Off-Hand'
        or role.get('names') != ['Malice']
        or set(role.get('qualities', [])) != {'normal', 'superior', 'low_quality'}
        or role.get('types') != ['swor']
        or role.get('mercenary_type') != 'Act 5 Frenzy'
        or set(role.get('important_stats', [])) != {'135:0', '17:0', '18:0', '19:0', '116:0'}
    ):
        raise ValueError('Malice wearer, contribution or exact reference differs')
    section = section_inventory(_read_pin(evidence['guide'], root))['sections'][25]
    if section['heading'] != 'Mercenary' or not all(
        phrase in section['text']
        for phrase in (
            "Act 5 Frenzy Mercenary with the full Sazabi's Set",
            'apply Open Wounds with Malice Mythical Sword',
            'Make sure to prebuff him with Demon Limb and Treachery Breast Plate',
        )
    ):
        raise ValueError('Malice guide setup evidence differs')
    if (
        role['source']['path'] != 'pricing/data/wp-a-builds.json'
        or role['source']['locator'] != '/echoing-strike-warlock-guide/variants/3/merc/Off-Hand/0'
    ):
        raise ValueError('Malice primary source differs')
    pin = review['recipe_source']
    if pin['path'] != 'third-parties/d2data/json/runes.json' or {**pin, 'locator': '/Malice'} not in role['source'].get(
        'corroborating', []
    ):
        raise ValueError('Malice recipe source differs')
    recipe = json.loads(_read_pin(pin, root))['Malice']
    if recipe.get('T1Code1') != 'openwounds' or recipe.get('T1Min1') != 100 or recipe.get('T1Max1') != 100:
        raise ValueError('Malice native contribution differs')
    if (
        item.get('base') != '7wd'
        or item.get('quality') != 7
        or item.get('ethereal') is not True
        or item.get('sockets') != 3
        or item.get('socketedItems') != [recipe[f'Rune{i}'] for i in range(1, 4)]
        or item.get('stats', {}).get('item_openwounds') != 100
    ):
        raise ValueError('Malice parent recipe/base/socket example differs')
    required = [('context_eq', 'player_class', 'Warlock'), ('context_eq', 'mercenary_type', 'Act 5 Frenzy')]
    required += [
        ('fact_eq', k, v)
        for k, v in (
            ('ethereal', True),
            ('identified', True),
            ('base_code', '7wd'),
            ('runeword', 'Malice'),
            ('sockets', 3),
            ('socket_contents', 'filled'),
        )
    ]
    if not all(requires_eq(role.get('must', {}), *claim) for claim in required):
        raise ValueError('Malice role omits exact applicability requirements')
    dependencies = role.get('depends_on', [])
    expected = [{'op': 'context_contains', 'field': 'mercenary_items', 'value': name} for name in COMPANIONS]
    if len(dependencies) != 3 or any(
        sum(d.get('when') == predicate for d in dependencies) != 1 for predicate in expected
    ):
        raise ValueError('Malice role omits full Sazabi mercenary companions')
