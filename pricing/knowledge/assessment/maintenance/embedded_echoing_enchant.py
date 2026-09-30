"""Validate the player Enchant prebuff separately from its mercenary recipient."""

import json

from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


GUIDE = 'pricing/raw/mr/guides__echoing-strike-warlock-guide.html'


def validate_echoing_enchant(review, resolved, role, root):
    evidence = review['evidence']
    context = resolved['context']
    recipient = context['span_index'] == 15
    section_id = 25 if recipient else 24
    if (
        evidence['guide']['path'] != GUIDE
        or context['span_index'] not in (12, 15)
        or context['side'] != ('merc' if recipient else 'player')
        or context['label'] != 'Demon Limb'
        or evidence['reference']['section_locator'] != f'/sections/{section_id}'
    ):
        raise ValueError('Echoing Enchant reference is outside the reviewed player context')
    section = section_inventory(_read_pin(evidence['guide'], root))['sections'][section_id]
    phrase = (
        'Make sure to prebuff him with Demon Limb and Treachery Breast Plate.'
        if recipient
        else 'Prebuffing with Demon Limb and Treachery Breast Plate gives better Attack Rating and Survivability.'
    )
    expected_role = (
        'echoing-ubers-mercenary-enchant-prebuff' if recipient else 'echoing-strike-warlock-guide-3-demon-limb-prebuff'
    )
    expected_source = (
        ('pricing/data/appraisal-guide-sections.json', f'/sources/{GUIDE.replace("/", "~1")}/sections/25')
        if recipient
        else ('pricing/data/wp-a-variants/echoing-strike-warlock-guide.json', '/variants/3')
    )
    if (
        section['heading'] != ('Mercenary' if recipient else 'Setup')
        or phrase not in section['text']
        or (recipient and 'Act 5 Frenzy Mercenary' not in section['text'])
        or role.get('id') != expected_role
        or role.get('build') != 'echoing-strike-warlock-guide'
        or role.get('variant') != 'Ubers'
        or role.get('side') != 'player'
        or role.get('slot') != 'Prebuff'
        or role.get('names') != ['Demon Limb']
        or role.get('qualities') != ['unique']
        or role.get('types') != ['club']
        or role.get('important_stats') != ['204:3351']
        or (role['source']['path'], role['source']['locator']) != expected_source
        or (
            recipient
            and (
                not requires_eq(role.get('must', {}), 'context_eq', 'mercenary_type', 'Act 5 Frenzy')
                or not requires_eq(role.get('must', {}), 'fact_eq', 'identified', True)
            )
        )
        or not requires_eq(role.get('must', {}), 'context_eq', 'player_class', 'Warlock')
        or not any(
            dependency.get('when') == {'op': 'charge_skill', 'skill_id': 52, 'value': 1}
            for dependency in role.get('depends_on', [])
        )
    ):
        raise ValueError('Echoing Enchant role changes wearer, contribution or charge requirement')
    pin = review['native_source']
    if pin['path'] != 'third-parties/d2data/json/uniqueitems.json':
        raise ValueError('Echoing Enchant requires native unique definition evidence')
    native = json.loads(_read_pin(pin, root))['296']
    if any(
        native.get(key) != value
        for key, value in {
            'index': 'Demonlimb',
            '*ID': 296,
            'code': '7sp',
            'prop4': 'charged',
            'par4': 'Enchant',
            'min4': 20,
            'max4': 23,
        }.items()
    ):
        raise ValueError('Echoing Enchant native identity or charge definition changed')
    item = resolved['item']
    if (
        item.get('base') != native['code']
        or item.get('quality') != 6
        or item.get('unique') != 'unique296'
        or item.get('stats', {}).get('item_charged_skill#52#23') != 20
    ):
        raise ValueError('Echoing Enchant tooltip has a different identity or charge skill')
