"""Review Echoing's exact starter and Prayer mercenary Insight tooltips."""

import json

from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.merc_survival_templates import legal_base_condition
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


GUIDE = 'pricing/raw/mr/guides__echoing-strike-warlock-guide.html'
CONTEXTS = {
    1: (0, 13, 'Starter', '9pa', 'Act 2 Blessed Aim'),
    6: (1, 17, 'Standard', '7wc', 'Act 2 Prayer'),
    8: (2, 21, 'Magic Find', '7wc', 'Act 2 Prayer'),
    127: ('overview', 42, 'Mercenary overview', '7wc', 'Act 2 Prayer'),
    130: ('overview', 43, 'Mercenary overview', '7wc', 'Act 2 Prayer'),
}


def validate_echoing_insight(review, resolved, role, root):
    evidence = review['evidence']
    context = CONTEXTS.get(resolved['context']['span_index'])
    if context is None or evidence['guide']['path'] != GUIDE:
        raise ValueError('Echoing Insight reference outside reviewed contexts')
    variant, section_id, name, base, mercenary = context
    overview = variant == 'overview'
    heading = 'Insight, Prayer' if overview else 'Mercenary'
    phrase = 'Desert Mercenary with Prayer Aura' if overview else mercenary + ' Mercenary'
    priorities = {'151:120'} if overview else {'151:120', '17:0', '18:0', '97:9', '119:0'}
    source_path = 'pricing/data/appraisal-guide-sections.json' if overview else 'pricing/data/wp-a-builds.json'
    source_locator = (
        '/sources/' + GUIDE.replace('/', '~1') + '/sections/42'
        if overview
        else f'/echoing-strike-warlock-guide/variants/{variant}'
    )
    sections = section_inventory(_read_pin(evidence['guide'], root))['sections']
    section = sections[section_id]
    if overview and section_id == 43:
        parent = sections[42]
        if parent['heading'] != 'Insight, Prayer' or 'Desert Mercenary with Prayer Aura' not in parent['text']:
            raise ValueError('Echoing Insight progression lacks its Prayer mercenary parent')
        heading, phrase = 'Gear Progression', 'The Mercenary'
        if 'Insight Giant Thresher' not in section['text']:
            raise ValueError('Echoing Insight progression lacks the weapon example')
    if (
        evidence['reference']['section_locator'] != f'/sections/{section_id}'
        or section['heading'] != heading
        or phrase not in section['text']
        or role.get('id') != f'echoing-{variant}-insight-merc'
        or role.get('variant') != name
        or role.get('build') != 'echoing-strike-warlock-guide'
        or role.get('side') != 'merc'
        or role.get('slot') != 'Weapon'
        or role.get('names') != ['Insight']
        or role.get('types') != ['pole']
        or set(role.get('qualities', [])) != {'normal', 'superior', 'low_quality'}
        or set(role.get('important_stats', [])) != priorities
        or role['source']['path'] != source_path
        or role['source']['locator'] != source_locator
    ):
        raise ValueError('Echoing Insight variant, bearer or contribution differs')
    native = review['recipe_source']
    if native['path'] != 'third-parties/d2data/json/runes.json' or {**native, 'locator': '/Insight'} not in role[
        'source'
    ].get('corroborating', []):
        raise ValueError('Echoing Insight lacks native recipe evidence')
    recipe = json.loads(_read_pin(native, root))['Insight']
    if (
        recipe.get('T1Code6') != 'aura'
        or recipe.get('T1Param6') != 'Meditation'
        or (recipe.get('T1Min6'), recipe.get('T1Max6')) != (12, 17)
    ):
        raise ValueError('Echoing Insight native aura changed')
    item = resolved['item']
    if (
        item.get('base') != base
        or item.get('quality') != 7
        or item.get('ethereal') is not True
        or item.get('sockets') != 4
        or item.get('socketedItems') != [recipe[f'Rune{i}'] for i in range(1, 5)]
    ):
        raise ValueError('Echoing Insight exact native example differs')
    required = [('context_eq', 'player_class', 'Warlock'), ('context_eq', 'mercenary_type', mercenary)]
    required += [
        ('fact_eq', k, v)
        for k, v in [
            ('identified', True),
            ('runeword', 'Insight'),
            ('sockets', 4),
            ('socket_contents', 'filled'),
        ]
    ]
    if not overview:
        required += [('fact_eq', 'base_code', base), ('fact_eq', 'ethereal', True)]
    else:
        expected = [{'op': op, 'field': key, 'value': value} for op, key, value in required]
        expected.append(legal_base_condition('Insight', ['pole']))

        def canonical(rows):
            return sorted(json.dumps(row, sort_keys=True) for row in rows)

        if canonical(role.get('must', {}).get('all', [])) != canonical(expected):
            raise ValueError('Echoing Insight general mana use has extra or missing requirements')
    if not all(requires_eq(role.get('must', {}), *claim) for claim in required):
        raise ValueError('Echoing Insight role omits applicability requirements')
    dependencies = role.get('depends_on', [])
    if variant in (1, 2):
        if len(dependencies) != 1 or dependencies[0].get('when') != {
            'op': 'context_contains',
            'field': 'mercenary_items',
            'value': 'Cure',
        }:
            raise ValueError('Echoing Insight Prayer setup lacks Cure dependency')
    elif dependencies:
        raise ValueError('Echoing Insight general or starter use must not inherit Cure requirements')
