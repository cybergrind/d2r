"""Exact Cure components; Cleansing and full-loadout healing are distinct claims."""

import json

from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.merc_survival_templates import legal_base_condition
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


GUIDE = 'pricing/raw/mr/guides__echoing-strike-warlock-guide.html'
CONTEXTS = {5: (1, 17, 'Standard'), 7: (2, 21, 'Magic Find'), 155: ('progression', 43, 'Mercenary progression')}


def validate_echoing_cure(review, resolved, role, root):
    evidence = review['evidence']
    context = CONTEXTS.get(resolved['context']['span_index'])
    if context is None or evidence['guide']['path'] != GUIDE:
        raise ValueError('Echoing Cure reference outside reviewed context')
    variant, section_id, name = context
    sections = section_inventory(_read_pin(evidence['guide'], root))['sections']
    section = sections[section_id]
    progression = variant == 'progression'
    role_id = 'echoing-progression-cure-merc' if progression else f'echoing-strike-warlock-guide-{variant}-merc-cure'
    if progression and (
        sections[42]['heading'] != 'Insight, Prayer'
        or 'Desert Mercenary with Prayer Aura' not in sections[42]['text']
        or 'Cure Grand Crown' not in section['text']
    ):
        raise ValueError('Echoing Cure progression lacks Prayer mercenary parent or helmet example')
    if (
        evidence['reference']['section_locator'] != f'/sections/{section_id}'
        or section['heading'] != ('Gear Progression' if progression else 'Mercenary')
        or ('The Mercenary' if progression else 'Act 2 Prayer Mercenary') not in section['text']
        or (not progression and resolved['context']['side'] != 'merc')
        or role.get('id') != role_id
        or role.get('build') != 'echoing-strike-warlock-guide'
        or role.get('variant') != name
        or role.get('side') != 'merc'
        or role.get('slot') != 'Helmet'
        or role.get('names') != ['Cure']
        or set(role.get('types', [])) != {'helm', 'circ'}
        or set(role.get('qualities', [])) != {'normal', 'superior', 'low_quality'}
        or set(role.get('important_stats', []))
        != ({'151:109'} if progression else {'151:109', '45:0', '110:0', '76:0', '99:0'})
        or role.get('depends_on')
        or role['source']['path']
        != ('pricing/data/appraisal-guide-sections.json' if progression else 'pricing/data/wp-a-builds.json')
        or role['source']['locator']
        != (
            '/sources/' + GUIDE.replace('/', '~1') + '/sections/43'
            if progression
            else f'/echoing-strike-warlock-guide/variants/{variant}'
        )
    ):
        raise ValueError('Echoing Cure wearer, source or component contribution differs')
    pin = review['recipe_source']
    if pin['path'] != 'third-parties/d2data/json/runes.json':
        raise ValueError('Echoing Cure native source differs')
    recipe = json.loads(_read_pin(pin, root))['Cure']
    expected = {
        'T1Code5': 'aura',
        'T1Param5': 'Cleansing',
        'T1Min5': 1,
        'T1Max5': 1,
        'T1Code3': 'res-pois',
        'T1Min3': 10,
        'T1Max3': 30,
    }
    if any(recipe.get(k) != v for k, v in expected.items()):
        raise ValueError('Echoing Cure native aura or Non-Ladder rolls differ')
    item = resolved['item']
    stats = item.get('stats', {})
    if (
        item.get('base') != 'xrn'
        or item.get('quality') != 7
        or item.get('ethereal') is not True
        or item.get('sockets') != 3
        or item.get('socketedItems') != [recipe[f'Rune{i}'] for i in range(1, 4)]
        or stats.get('item_aura#109') != 1
        or not 10 <= stats.get('poisonresist', -1) <= 30
    ):
        raise ValueError('Echoing Cure native parent/socket example differs')
    required = [('context_eq', 'player_class', 'Warlock'), ('context_eq', 'mercenary_type', 'Act 2 Prayer')]
    required += [
        ('fact_eq', k, v)
        for k, v in [
            ('identified', True),
            ('runeword', 'Cure'),
            ('sockets', 3),
            ('socket_contents', 'filled'),
        ]
    ]
    if progression:
        expected = [{'op': op, 'field': key, 'value': value} for op, key, value in required]
        expected.append(legal_base_condition('Cure', ['helm', 'circ']))
        actual = role.get('must', {}).get('all', [])
        if sorted(json.dumps(r, sort_keys=True) for r in actual) != sorted(
            json.dumps(r, sort_keys=True) for r in expected
        ):
            raise ValueError('Echoing Cure progression has extra or missing requirements')
    else:
        required += [('fact_eq', 'base_code', 'xrn'), ('fact_eq', 'ethereal', True)]
    if not all(requires_eq(role.get('must', {}), *claim) for claim in required):
        raise ValueError('Echoing Cure applicability requirements differ')
