"""Gold-farming boots and an Echoing spear: useful stats depend on the wearer."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BOOT_ROLE = 'gold-find-barbarian-infernostride-equipment-tail-alternative'
SPEAR_ROLE = 'echoing-strike-warlock-guide-arioc-s-needle-specialist-equipment-alternative'
BOOTS = Item(
    'Demonhide Boots',
    'unique',
    'Infernostride',
    ((48, 0, 12), (49, 0, 33), (96, 0, 20), (40, 0, 10), (39, 0, 30), (89, 0, 2), (16, 0, 120), (79, 0, 40)),
    named_table_id=237,
)
SPEAR = Item(
    'Hyperion Spear',
    'unique',
    "Arioc's Needle",
    ((17, 0, 180), (18, 0, 180), (141, 0, 50), (115, 0, 1), (127, 0, 2), (93, 0, 30)),
    named_table_id=382,
)


def cases():
    for role, original, klass, keys, excluded, locator in (
        (
            BOOT_ROLE,
            BOOTS,
            'Barbarian',
            ('79:0', '96:0', '39:0', '40:0'),
            ('48:0', '49:0'),
            '/gold-find-barbarian/slots/Boots/0',
        ),
        (
            SPEAR_ROLE,
            SPEAR,
            'Warlock',
            ('17:0', '18:0', '127:0', '141:0', '115:0'),
            ('93:0',),
            '/echoing-strike-warlock-guide/slots/Weapon/13',
        ),
    ):
        context = {'player_class': klass}
        config = role + '-stats'
        variants = [
            ('native-minimum', original, context, 'true'),
            ('wrong-class', original, {'player_class': 'Amazon'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown'),
            ('unidentified', replace(original, identified=False), context, 'false'),
        ]
        if role == BOOT_ROLE:
            variants.extend(
                (
                    (
                        'maximum-rolls',
                        replace(original, raw_stats=(*BOOTS.raw_stats[:6], (16, 0, 150), (79, 0, 70))),
                        context,
                        'true',
                    ),
                    ('upgraded', replace(original, base='Wyrmhide Boots'), context, 'true'),
                    ('ethereal', replace(original, ethereal=True), context, 'false'),
                    ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
                    (
                        'illegal-socket',
                        replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                        context,
                        'false',
                    ),
                )
            )
        else:
            variants.extend(
                (
                    (
                        'maximum-rolls',
                        replace(
                            original,
                            raw_stats=((17, 0, 230), (18, 0, 230), (141, 0, 50), (115, 0, 1), (127, 0, 4), (93, 0, 30)),
                        ),
                        context,
                        'true',
                    ),
                    ('ethereal-casting-use', replace(original, ethereal=True), context, 'true'),
                    ('unknown-ethereal-casting-use', replace(original, ethereal=None), context, 'true'),
                    (
                        'open-socket',
                        replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                        context,
                        'true',
                    ),
                    (
                        'illegal-two-sockets',
                        replace(original, sockets=2, raw_stats=(*original.raw_stats, (194, 0, 2))),
                        context,
                        'false',
                    ),
                )
            )
        for label, item, ctx, truth in variants:
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'farming-specialist-uniques/{original.named_table_id}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(excluded, (config,)),
                report_contains=(
                    original.name,
                    'Trade tier:',
                    *(('(40-70%)', '(120-150%)') if role == BOOT_ROLE else ('(180-230%)', '(2-4)')),
                )
                if active and label in ('native-minimum', 'maximum-rolls')
                else (original.name, 'Trade tier:')
                if active
                else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:' + locator,
                    'third-parties/d2data/json/uniqueitems.json:/' + str(original.named_table_id),
                ),
            )


CASES = tuple(cases())
