"""Fleshripper supports Smite via CB/OW, not weapon ED, DS, or target defense."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'smite-paladin-fleshripper-attack-utility-alternative'
CONFIG = ROLE + '-stats'
RAW = ((17, 0, 200), (18, 0, 200), (116, 0, 50), (117, 0, 1), (136, 0, 25), (135, 0, 50), (141, 0, 33), (150, 0, 20))
ITEM = Item('Fanged Knife', 'unique', 'Fleshripper', RAW, complete=True, named_table_id=304)


def cases():
    context = {'player_class': 'Paladin'}
    for label, item, ctx, truth in (
        ('minimum-ed', ITEM, context, 'true'),
        (
            'maximum-ed',
            replace(ITEM, raw_stats=tuple((s, p, 300 if s in (17, 18) else v) for s, p, v in RAW)),
            context,
            'true',
        ),
        ('ethereal-no-indestructible', replace(ITEM, ethereal=True), context, 'false'),
        ('ethereal-unknown-indestructible', replace(ITEM, ethereal=True, complete=False), context, 'unknown'),
        (
            'ethereal-zod',
            replace(
                ITEM,
                ethereal=True,
                sockets=1,
                socket_contents='filled',
                raw_stats=(*RAW, (194, 0, 1), (152, 0, 1)),
                socket_items=(SocketItem('Zod Rune'),),
            ),
            context,
            'true',
        ),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
        ('unknown-sockets', replace(ITEM, sockets=None, socket_contents='unknown'), context, 'unknown'),
        ('wrong-class', ITEM, {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('unidentified', replace(ITEM, identified=False), context, 'false'),
    ):
        active = truth == 'true'
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if active:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(CONFIG)) for key in ('136:0', '135:0', '150:0')}
                )
            )
        yield Case(
            id='smite-fleshripper/' + label,
            item=item,
            context=ctx,
            covers=(ROLE,),
            scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if active else (CONFIG,),
            absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '116:0', '117:0', '141:0'), (CONFIG,)),
            report_contains=('Fleshripper', 'Trade tier:', '25% Chance of Crushing Blow', '50% Chance of Open Wounds')
            + (('Sockets: 1 — Zod',) if label == 'ethereal-zod' else ())
            if active
            else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/smite-paladin/slots/Weapon/5',
                'third-parties/d2data/json/uniqueitems.json:/304',
            ),
        )


CASES = tuple(cases())
