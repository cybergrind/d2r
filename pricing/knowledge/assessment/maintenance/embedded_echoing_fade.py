"""Bind Echoing's player/mercenary Fade examples to distinct temporary-use rules."""

import json

from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


CONTEXTS = {13: (24, 'player'), 16: (25, 'merc')}
GUIDE = 'pricing/raw/mr/guides__echoing-strike-warlock-guide.html'


def validate_echoing_fade(review, resolved, role, root):
    evidence = review['evidence']
    context = CONTEXTS.get(resolved['context']['span_index'])
    if context is None or evidence['guide']['path'] != GUIDE:
        raise ValueError('Echoing Fade reference is outside the reviewed contexts')
    section_id, side = context
    guide = section_inventory(_read_pin(evidence['guide'], root))
    section = guide['sections'][section_id]
    phrase = (
        'Prebuffing with Demon Limb and Treachery Breast Plate'
        if side == 'player'
        else 'Make sure to prebuff him with Demon Limb and Treachery Breast Plate'
    )
    expected_locator = f'/sources/{GUIDE.replace("/", "~1")}/sections/{section_id}'
    if (
        evidence['reference']['section_locator'] != f'/sections/{section_id}'
        or section['heading'] != ('Setup' if side == 'player' else 'Mercenary')
        or phrase not in section['text']
        or (side == 'merc' and 'Act 5 Frenzy Mercenary' not in section['text'])
        or role.get('id') != f'echoing-ubers-{side}-fade-prebuff'
        or role.get('build') != 'echoing-strike-warlock-guide'
        or role.get('variant') != 'Ubers'
        or role.get('side') != side
        or role.get('slot') != 'Prebuff'
        or role.get('names') != ['Treachery']
        or role.get('types') != ['tors']
        or role.get('important_stats') != ['201:17103']
        or role['source']['path'] != 'pricing/data/appraisal-guide-sections.json'
        or role['source']['locator'] != expected_locator
    ):
        raise ValueError('Echoing Fade wearer, contribution or source differs')
    pin = review['recipe_source']
    if pin['path'] != 'third-parties/d2data/json/runes.json' or {**pin, 'locator': '/Treachery'} not in role[
        'source'
    ].get('corroborating', []):
        raise ValueError('Echoing Fade native recipe evidence differs')
    recipe = json.loads(_read_pin(pin, root))['Treachery']
    if any(
        recipe.get(key) != value
        for key, value in {
            'T1Code2': 'gethit-skill',
            'T1Param2': 'Fade',
            'T1Min2': 5,
            'T1Max2': 15,
        }.items()
    ):
        raise ValueError('Echoing Fade native trigger semantics changed')
    item = resolved['item']
    if (
        item.get('base') != 'brs'
        or item.get('quality') != 7
        or item.get('sockets') != 3
        or item.get('socketedItems') != [recipe[f'Rune{i}'] for i in range(1, 4)]
        or not str(item.get('unique', '')).startswith('runeword')
    ):
        raise ValueError('Echoing Fade tooltip has another base or recipe')
    required = [('context_eq', 'player_class', 'Warlock')]
    if side == 'merc':
        required.append(('context_eq', 'mercenary_type', 'Act 5 Frenzy'))
    required.extend(
        ('fact_eq', key, value)
        for key, value in (
            ('identified', True),
            ('base_code', 'brs'),
            ('runeword', 'Treachery'),
            ('sockets', 3),
            ('socket_contents', 'filled'),
        )
    )
    if not all(requires_eq(role.get('must', {}), *claim) for claim in required):
        raise ValueError('Echoing Fade role omits reviewed applicability requirements')
