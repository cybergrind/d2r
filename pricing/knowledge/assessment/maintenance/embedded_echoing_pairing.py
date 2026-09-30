"""Bind the reviewed Ubers magic-pierce pairing to its exact native tooltip."""

import json

from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.policies.sources import resolve_pointer


GUIDE = 'pricing/raw/mr/guides__echoing-strike-warlock-guide.html'
COMPANIONS = frozenset({"Hellwarden's Will", 'Renewed Black Cleft'})


def validate_echoing_pairing(review, resolved, role, root):
    evidence = review['evidence']
    context = resolved['context']
    if context['span_index'] == 9:
        return validate_hellwarden(review, resolved, role, root)
    if (
        evidence['guide']['path'] != GUIDE
        or context['span_index'] != 10
        or context['side'] != 'player'
        or context['label'] != 'Sling'
        or evidence['reference']['section_locator'] != '/sections/24'
    ):
        raise ValueError('Echoing pairing reference is outside the reviewed Sling context')
    section = section_inventory(_read_pin(evidence['guide'], root))['sections'][24]
    source = role['source']
    if (
        section['heading'] != 'Setup'
        or "Hellwarden's Will + Sling and a Sunder Charm with -xx% Enemy Magic Resistance" not in section['text']
        or role.get('id') != 'echoing-ubers-sling-magic-pierce'
        or role.get('build') != 'echoing-strike-warlock-guide'
        or role.get('variant') != 'Ubers'
        or role.get('side') != 'player'
        or role.get('slot') != 'Ring'
        or role.get('names') != ['Sling']
        or role.get('qualities') != ['unique']
        or role.get('types') != ['ring']
        or role.get('important_stats') != ['358:0', '105:0']
        or source['path'] != 'pricing/data/appraisal-guide-sections.json'
        or source['locator'] != f'/sources/{GUIDE.replace("/", "~1")}/sections/24'
    ):
        raise ValueError('Echoing pairing role changes source, wearer or contribution')
    # Exact reviewed applicability: do not turn the guide's perfect example into
    # a minimum-roll requirement or relax the native ring's legal facets.
    required = [
        {'op': 'context_eq', 'field': 'player_class', 'value': 'Warlock'},
        *[
            {'op': 'fact_eq', 'field': field, 'value': value}
            for field, value in (
                ('identified', True),
                ('base_code', 'rin'),
                ('ethereal', False),
                ('sockets', 0),
                ('socket_contents', 'empty'),
            )
        ],
    ]
    must = role.get('must', {})

    if set(must) != {'all'} or canonical(must['all']) != canonical(required):
        raise ValueError('Echoing pairing changes the reviewed class, ring or roll requirements')
    dependencies = [d.get('when') for d in role.get('depends_on', [])]
    expected = [{'op': 'context_contains', 'field': 'player_items', 'value': name} for name in COMPANIONS]
    if canonical(dependencies) != canonical(expected):
        raise ValueError('Echoing pairing loses required player companions')
    pin = review['native_source']
    if pin['path'] != 'third-parties/d2data/json/uniqueitems.json' or {**pin, 'locator': '/415'} not in source.get(
        'corroborating', []
    ):
        raise ValueError('Echoing pairing lacks native unique evidence')
    native = json.loads(_read_pin(pin, root))['415']
    if any(
        native.get(key) != value
        for key, value in {
            'index': 'Sling',
            '*ID': 415,
            'code': 'rin',
            'prop2': 'cast1',
            'min2': 10,
            'max2': 10,
            'prop3': 'pierce-mag',
            'min3': 3,
            'max3': 5,
        }.items()
    ):
        raise ValueError('Echoing pairing native identity or contributing rolls changed')
    item = resolved['item']
    stats = item.get('stats', {})
    if (
        item.get('unique') != 'unique415'
        or item.get('base') != native['code']
        or item.get('quality') != 6
        or item.get('sockets') != 0
        or item.get('ethereal') is not False
        or stats.get('item_fastercastrate') != 10
        or stats.get('passive_mag_pierce') not in (3, 4, 5)
    ):
        raise ValueError('Echoing pairing tooltip has another identity or invalid contribution')


def canonical(predicates):
    return sorted(json.dumps(p, sort_keys=True) for p in predicates)


def validate_hellwarden(review, resolved, role, root):
    evidence = review['evidence']
    context = resolved['context']
    phrase = "Hellwarden's Will + Sling and a Sunder Charm with -xx% Enemy Magic Resistance"
    if (
        evidence['guide']['path'] != GUIDE
        or context['label'] != "Hellwarden's Will"
        or context['side'] != 'player'
        or evidence['reference']['section_locator'] != '/sections/24'
    ):
        raise ValueError('Echoing pairing helmet is outside the reviewed Ubers context')
    section = section_inventory(_read_pin(evidence['guide'], root))['sections'][24]
    source = role['source']
    if (
        section['heading'] != 'Setup'
        or phrase not in section['text']
        or role.get('id') != 'echoing-ubers-hellwarden'
        or role.get('build') != 'echoing-strike-warlock-guide'
        or role.get('variant') != 'Ubers'
        or role.get('side') != 'player'
        or role.get('slot') != 'Helmet'
        or role.get('names') != ["Hellwarden's Will"]
        or role.get('types') != ['helm']
        or role.get('qualities') != ['unique']
        or role.get('important_stats') != ['358:0', '127:0', '105:0']
        or role.get('required_socket_item') != "Guardian's Light"
        or source['path'] != 'pricing/data/wp-a-builds.json'
        or source['locator'] != '/echoing-strike-warlock-guide/variants/3'
    ):
        raise ValueError('Echoing pairing helmet changes wearer, source or contribution')
    primary = resolve_pointer(json.loads(_read_pin(source, root)), source['locator'])
    if phrase not in json.dumps(primary, ensure_ascii=False):
        raise ValueError('Echoing pairing helmet source does not endorse the same setup')
    required = [
        {'op': 'context_eq', 'field': 'player_class', 'value': 'Warlock'},
        {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
        *[
            {'op': 'stat_at_least', 'key': key, 'value': value, 'absent_is_zero': True}
            for key, value in [('358:0', 5), ('127:0', 1), ('105:0', 20)]
        ],
    ]
    must = role.get('must', {})
    if set(must) != {'all'} or canonical(must['all']) != canonical(required):
        raise ValueError('Echoing pairing helmet changes the applicability requirements')
    dependencies = [d.get('when') for d in role.get('depends_on', [])]
    expected = [
        {'op': 'context_contains', 'field': 'player_items', 'value': name} for name in ('Sling', 'Renewed Black Cleft')
    ]
    preferences = role.get('preferences', [])
    if (
        canonical(dependencies) != canonical(expected)
        or len(preferences) != 1
        or preferences[0].get('when') != {'op': 'innate_stat_at_least', 'key': '358:0', 'value': 8}
    ):
        raise ValueError('Echoing pairing helmet loses companions or native-roll semantics')
    pin = review['native_source']
    if pin['path'] != 'third-parties/d2data/json/uniqueitems.json':
        raise ValueError('Echoing pairing helmet requires native item definitions')
    definitions = json.loads(_read_pin(pin, root))
    for identity, fields in {
        '419': {
            'index': 'Unique Warlock Helm',
            '*ID': 419,
            'code': 'xsk',
            'prop1': 'allskills',
            'min1': 1,
            'max1': 1,
            'prop3': 'pierce-mag',
            'min3': 5,
            'max3': 8,
            'prop4': 'cast1',
            'min4': 20,
            'max4': 20,
        },
        '425': {'index': "Guardian's Light", '*ID': 425, 'code': 'cjw', 'prop4': 'pierce-mag', 'min4': 5, 'max4': 10},
    }.items():
        if any(definitions[identity].get(key) != value for key, value in fields.items()):
            raise ValueError('Echoing pairing helmet or jewel native definition changed')
    item = resolved['item']
    links = item.get('socketedItems', [])
    child = resolved['socket_definitions'].get(str(links[0]), {}) if len(links) == 1 else {}
    stats, child_stats = item.get('stats', {}), child.get('stats', {})
    if (
        item.get('unique') != 'unique419'
        or item.get('base') != 'xsk'
        or item.get('quality') != 6
        or item.get('sockets') != 1
        or item.get('ethereal') not in (None, False)
        or stats.get('item_allskills') != 1
        or stats.get('item_fastercastrate') != 20
        or stats.get('passive_mag_pierce') not in range(5, 9)
        or child.get('unique') != 'unique425'
        or child.get('base') != 'cjw'
        or child.get('quality') != 6
        or child_stats.get('passive_mag_pierce') not in range(5, 11)
    ):
        raise ValueError('Echoing pairing helmet or linked jewel has a different identity or invalid native roll')
