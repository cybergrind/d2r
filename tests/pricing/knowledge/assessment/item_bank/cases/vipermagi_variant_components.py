"""Variant armor utility keeps explicit base and full-loadout gates separate."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.vipermagi_caster_alternatives import MAXIMUM, MINIMUM
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


# Upgrade eligibility follows generic identity versus explicit Serpentskin citations.
USES = (
    ('enchant-sorceress', 1, 'Sorceress', True, False, False),
    ('enchant-sorceress', 2, 'Sorceress', True, False, False),
    ('fist-of-the-heavens-paladin', 4, 'Paladin', False, False, False),
    ('meteor-sorceress', 4, 'Sorceress', True, True, True),
    ('nova-sorceress-guide', 1, 'Sorceress', False, True, False),
    ('nova-sorceress-guide', 2, 'Sorceress', False, True, False),
)


def cases():
    for build, index, klass, upgrades, fcr, fhr in USES:
        role = f'{build}-{index}-vipermagi'
        config = role + '-stats'
        item = Item('Serpentskin Armor', 'unique', 'Skin of the Vipermagi', MINIMUM)
        context = {
            'player_class': klass,
            **({'player_total_fcr': 105} if fcr else {}),
            **({'player_total_fhr': 86} if fhr else {}),
        }
        examples = [
            ('minimum', item, context, 'true'),
            ('maximum', replace(item, raw_stats=MAXIMUM), context, 'true'),
            ('upgraded', replace(item, base='Wyrmhide'), context, 'true' if upgrades else 'false'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {**context, 'player_class': 'Druid'}, 'false'),
            ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
            ('open-socket', replace(item, sockets=1), context, 'true'),
            ('unknown-socket-contents', replace(item, sockets=1, socket_contents='unknown'), context, 'true'),
            (
                'unrelated-ias-jewel',
                replace(
                    item,
                    sockets=1,
                    socket_contents='filled',
                    socket_items=(SocketItem('Jewel', ((93, 0, 15),), complete=True),),
                    raw_stats=(*MINIMUM, (93, 0, 15)),
                ),
                context,
                'true',
            ),
        ]
        for field, required, threshold in (('player_total_fcr', fcr, 105), ('player_total_fhr', fhr, 86)):
            examples.extend(
                (
                    (field + '-below', item, {**context, field: threshold - 1}, 'false' if required else 'true'),
                    (
                        field + '-unknown',
                        item,
                        {k: v for k, v in context.items() if k != field},
                        'unknown' if required else 'true',
                    ),
                )
            )
        for label, candidate, loadout, truth in examples:
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        rule_trace=IsPartialDict(truth=truth),
                        status='partial'
                        if truth == 'true'
                        else ('unknown' if not candidate.identified else 'failed' if truth == 'false' else 'partial'),
                    )
                )
            }
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in ('127:0', '105:0', '39:0', '41:0', '43:0', '45:0')
                        }
                    )
                )
            yield Case(
                id=f'vipermagi-component/{build}/{index}/{label}',
                item=candidate,
                context=loadout,
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if truth == 'true' else (config,),
                absent_stat_configurations={'93:0': (config,)},
                report_contains=('Skin of the Vipermagi', 'Trade tier:', '30% Faster Cast Rate')
                if candidate.identified
                else (),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/variants/{index}',
                    'third-parties/d2data/json/uniqueitems.json:/210',
                ),
            )


CASES = tuple(cases())
