"""Bound the late-game Teleport recommendation to its native recipe and wearer."""

import json

from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.merc_survival_templates import legal_base_condition


GUIDE = 'pricing/raw/mr/guides__echoing-strike-warlock-guide.html'


def validate_echoing_enigma(review, resolved, role, root):
    evidence = review['evidence']
    context = resolved['context']
    if (
        evidence['guide']['path'] != GUIDE
        or evidence['reference']['section_locator'] != '/sections/30'
        or context['span_index'] != 18
        or context['label'] != 'Enigma Mage Plate'
        or context['side'] != 'player'
    ):
        raise ValueError('Echoing Enigma reference outside reviewed late-game context')
    section = section_inventory(_read_pin(evidence['guide'], root))['sections'][30]
    if (
        section['heading'] != 'Late-Game'
        or 'Once you acquire Enigma Mage Plate, replace Blade Warp with Teleport.' not in section['text']
        or role.get('id') != 'echoing-late-game-enigma-player'
        or role.get('build') != 'echoing-strike-warlock-guide'
        or role.get('variant') != 'Late-Game'
        or role.get('side') != 'player'
        or role.get('slot') != 'Body Armor'
        or role.get('names') != ['Enigma']
        or role.get('types') != ['tors']
        or set(role.get('qualities', [])) != {'normal', 'superior', 'low_quality'}
        or role.get('important_stats') != ['97:54']
        or role.get('depends_on')
        or role['source']['path'] != 'pricing/data/appraisal-guide-sections.json'
        or role['source']['locator'] != '/sources/' + GUIDE.replace('/', '~1') + '/sections/30'
    ):
        raise ValueError('Echoing Enigma player mobility contribution differs')
    pin = review['recipe_source']
    if pin['path'] != 'third-parties/d2data/json/runes.json' or {**pin, 'locator': '/Enigma'} not in role['source'].get(
        'corroborating', []
    ):
        raise ValueError('Echoing Enigma lacks reviewed native recipe')
    recipe = json.loads(_read_pin(pin, root))['Enigma']
    if any(
        recipe.get(k) != v for k, v in {'T1Code7': 'oskill', 'T1Param7': 'Teleport', 'T1Min7': 1, 'T1Max7': 1}.items()
    ):
        raise ValueError('Echoing Enigma native Teleport changed')
    item = resolved['item']
    if (
        item.get('base') != 'xtp'
        or item.get('quality') != 7
        or item.get('sockets') != 3
        or item.get('socketedItems') != [recipe[f'Rune{i}'] for i in range(1, 4)]
        or item.get('stats', {}).get('item_nonclassskill#54') != 1
    ):
        raise ValueError('Echoing Enigma native example differs')
    required = [{'op': 'context_eq', 'field': 'player_class', 'value': 'Warlock'}]
    required.extend(
        {'op': 'fact_eq', 'field': k, 'value': v}
        for k, v in [
            ('identified', True),
            ('ethereal', False),
            ('runeword', 'Enigma'),
            ('sockets', 3),
            ('socket_contents', 'filled'),
        ]
    )
    required.append(legal_base_condition('Enigma', ['tors']))

    def canonical(rows):
        return sorted(json.dumps(r, sort_keys=True) for r in rows)

    if canonical(role.get('must', {}).get('all', [])) != canonical(required):
        raise ValueError('Echoing Enigma has extra or missing applicability requirements')
