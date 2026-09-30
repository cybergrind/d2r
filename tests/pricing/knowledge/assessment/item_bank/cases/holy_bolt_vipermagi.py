"""The cited Holy Bolt support armor requires Ber, without an invented FCR gate."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.vipermagi_payloads import ITEM
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem


ROLE = 'fist-of-the-heavens-paladin-4-vipermagi-ber'
ARMOR = replace(ITEM, raw_stats=(*ITEM.raw_stats, (36, 0, 8)), socket_items=(SocketItem('Ber Rune'),))


def cases():
    ctx = {'player_class': 'Paladin'}
    for label, item, context, truth in (
        ('native-minimum', ARMOR, ctx, 'true'),
        ('wrong-rune', replace(ARMOR, socket_items=(SocketItem('Ist Rune'),)), ctx, 'false'),
        ('unread-rune', replace(ARMOR, socket_items=()), ctx, 'unknown'),
        ('empty-socket', replace(ARMOR, socket_contents='empty', socket_items=()), ctx, 'false'),
        ('ethereal', replace(ARMOR, ethereal=True), ctx, 'false'),
        ('unknown-ethereal', replace(ARMOR, ethereal=None), ctx, 'unknown'),
        ('wrong-class', ARMOR, {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', ARMOR, {}, 'unknown'),
        ('upgraded-not-cited', replace(ARMOR, base='Wyrmhide'), ctx, 'false'),
        ('own-fcr-only', ARMOR, {**ctx, 'player_total_fcr': 30}, 'true'),
    ):
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                        for key in ('105:0', '127:0', '36:0')
                    }
                )
            )
        yield Case(
            id='holy-bolt-vipermagi/' + label,
            item=item,
            context=context,
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if truth == 'true' else (ROLE + '-stats',),
            report_contains=('Skin of the Vipermagi', 'Trade tier:'),
            evidence=(
                'pricing/raw/mr/planners/s10106pr.json:/data',
                'pricing/data/wp-a-builds.json:/fist-of-the-heavens-paladin/variants/4',
            ),
        )


CASES = tuple(cases())
