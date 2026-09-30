"""Zeal utility cases backed by cached gear footnotes and native affixes."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CONTEXT = {
    'player_class': 'Paladin',
    'player_level': 80,
    'player_strength': 150,
    'player_dexterity': 100,
    'player_items': [],
}
EVIDENCE = ('pricing/raw/mr/guides__zeal-paladin.html:gear-notes-1-4',)
# Native encoding: skill in high bits of layer; low6 bits are skill level.
# Charges: low8 bits remaining, next8 capacity. One remaining is enough for utility.
ITEMS = (
    (
        'demon-limb',
        Item('Tyrant Club', 'unique', 'Demon Limb', ((204, 3351, 1 | (20 << 8)),)),
        'demon-limb-zeal-footnote-swap',
        '204:3351',
    ),
    (
        'naj',
        Item('Elder Staff', 'set', "Naj's Puzzler", ((204, 3467, 1 | (69 << 8)),)),
        'najs-puzzler-zeal-footnote-swap',
        '204:3467',
    ),
    (
        'life-tap-wand',
        Item('Bone Wand', 'magic', raw_stats=((204, 5249, 1 | (60 << 8)),)),
        'zeal-paladin-life-tap-wand-footnote',
        '204:5249',
    ),
    (
        'teleport-staff',
        Item('Gnarled Staff', 'magic', raw_stats=((204, 3457, 1 | (30 << 8)),)),
        'zeal-paladin-teleport-staff-footnote',
        '204:3457',
    ),
    (
        'teleport-amulet-magic',
        Item('Amulet', 'magic', raw_stats=((204, 3457, 1 | (20 << 8)),)),
        'zeal-paladin-teleport-amulet-footnote',
        '204:3457',
    ),
    (
        'teleport-amulet',
        Item('Amulet', 'rare', raw_stats=((204, 3457, 1 | (20 << 8)),)),
        'zeal-paladin-teleport-amulet-footnote',
        '204:3457',
    ),
)


def role_expectation(role, *, status=None):
    fields = {'id': role, 'build': 'zeal-paladin'}
    if status:
        fields['status'] = status
    return IsPartialDict(roles=Contains(IsPartialDict(**fields)))


def cases():
    result = []
    for label, item, role, key in ITEMS:
        result.append(
            Case(
                id='zeal/' + label + '/available',
                item=item,
                context=CONTEXT,
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(IsPartialDict(id=role, build='zeal-paladin')),
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(role + '-stats'))})
                        ),
                    ),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                covers=(role,),
                report_contains=(item.name or item.base, 'Charges'),
                evidence=EVIDENCE,
            )
        )
        stat, layer, raw = item.raw_stats[0]
        result.append(
            Case(
                id='zeal/' + label + '/exhausted',
                item=replace(item, raw_stats=((stat, layer, raw & ~255),)),
                context=CONTEXT,
                expected={'assessment': role_expectation(role)},
                covers=(role,),
                scenario='negative',
                absent_annotations=(key,),
                evidence=EVIDENCE,
            )
        )
        result.append(
            Case(
                id='zeal/' + label + '/wrong-class',
                item=item,
                context={**CONTEXT, 'player_class': 'Sorceress'},
                expected={'assessment': role_expectation(role, status='failed')},
                covers=(role,),
                scenario='negative',
                absent_configurations=(role + '-stats',),
                evidence=EVIDENCE,
            )
        )
    for label, item, role, _key in ITEMS:
        if 'teleport' in label or label == 'naj':
            result.append(
                Case(
                    id='zeal/' + label + '/enigma',
                    item=item,
                    context={**CONTEXT, 'player_items': ['Enigma']},
                    expected={
                        'assessment': IsPartialDict(
                            roles=Contains(IsPartialDict(id=role, status='partial')),
                            stat_evaluation=IsPartialDict(
                                configurations=Contains(IsPartialDict(role_id=role, status='conditional'))
                            ),
                        )
                    },
                    covers=(role,),
                    scenario='negative',
                    absent_configurations=(role + '-stats',),
                    evidence=EVIDENCE,
                )
            )
    for label, item, role, key in ITEMS:
        result.append(
            Case(
                id='zeal/' + label + '/unknown-charges',
                item=replace(item, raw_stats=()),
                context=CONTEXT,
                expected={'assessment': role_expectation(role)},
                covers=(role,),
                scenario='unknown',
                absent_annotations=(key,),
                evidence=EVIDENCE,
            )
        )
    return tuple(result)


def additional_utility_cases():
    result = []
    examples = (
        (
            'wizard-casting',
            Item('Bone Knife', 'unique', 'Wizardspike', ((105, 0, 50),)),
            'wizardspike-zeal-footnote-swap',
            '105:0',
            (),
        ),
        (
            'fade-prebuff',
            Item(
                'Mage Plate',
                'normal',
                'Treachery',
                ((201, 17103, 5), (93, 0, 45), (99, 0, 20), (43, 0, 30)),
                sockets=3,
                socket_contents='filled',
                runeword='Treachery',
            ),
            'zeal-paladin-treachery-fade-prebuff',
            '201:17103',
            ('93:0', '99:0', '43:0'),
        ),
    )
    for label, item, role, key, nontransferred in examples:
        rows = [
            ('available', 'positive', item, CONTEXT),
            ('wrong-class', 'negative', item, {**CONTEXT, 'player_class': 'Sorceress'}),
            ('unknown-class', 'unknown', item, {k: v for k, v in CONTEXT.items() if k != 'player_class'}),
            ('ethereal', 'negative', replace(item, ethereal=True), CONTEXT),
            ('unknown-ethereal', 'unknown', replace(item, ethereal=None), CONTEXT),
            ('missing-use-stat', 'unknown', replace(item, raw_stats=()), CONTEXT),
        ]
        if label == 'fade-prebuff':
            rows.extend(
                [
                    ('empty-sockets', 'negative', replace(item, socket_contents='empty'), CONTEXT),
                    ('wrong-sockets', 'negative', replace(item, sockets=2), CONTEXT),
                    ('unknown-recipe', 'unknown', replace(item, runeword=None), CONTEXT),
                ]
            )
        for variant, scenario, candidate, context in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, build='zeal-paladin'))}
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(role + '-stats')),
                        }
                    )
                )
            result.append(
                Case(
                    id=f'zeal/{label}/{variant}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(nontransferred, (role + '-stats',)),
                    report_contains=(item.name,),
                    evidence=EVIDENCE,
                )
            )
    return tuple(result)


CASES = cases() + additional_utility_cases()
