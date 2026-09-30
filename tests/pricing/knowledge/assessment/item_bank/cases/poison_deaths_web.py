"""Poison Nova's Death's Web alternative values casting stats without an ethereal ban."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'poison-nova-necromancer-death-s-web-caster-utility-alternative'
STATS = ((127, 0, 2), (188, 17, 1), (336, 0, 40), (86, 0, 7), (138, 0, 7))
ITEM = Item('Unearthed Wand', 'unique', "Death's Web", STATS)


def cases():
    context = {'player_class': 'Necromancer'}
    rows = (
        ('minimum-rolls', ITEM, context, 'true'),
        (
            'maximum-rolls',
            replace(ITEM, raw_stats=((127, 0, 2), (188, 17, 2), (336, 0, 50), (86, 0, 12), (138, 0, 12))),
            context,
            'true',
        ),
        ('ethereal-casting', replace(ITEM, ethereal=True), context, 'true'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'true'),
        ('one-empty-socket', replace(ITEM, sockets=1), context, 'true'),
        ('unknown-contents', replace(ITEM, sockets=1, socket_contents='unknown'), context, 'true'),
        ('impossible-sockets', replace(ITEM, sockets=2), context, 'false'),
        ('unknown-sockets', replace(ITEM, sockets=None), context, 'unknown'),
        ('wrong-class', ITEM, {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('unidentified', replace(ITEM, identified=False), context, 'false'),
    )
    for label, item, loadout, truth in rows:
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                        for key in ('127:0', '188:17', '336:0', '86:0', '138:0')
                    }
                )
            )
        yield Case(
            id=f'poison-deaths-web/{label}',
            item=item,
            context=loadout,
            expected={'assessment': IsPartialDict(**expected)},
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            absent_configurations=() if truth == 'true' else (ROLE + '-stats',),
            report_contains=("Death's Web", 'Trade tier:', '(40-50%)')
            if truth == 'true' and label != 'unknown-contents'
            else ("Death's Web",),
            report_absent=('(40-50%)',) if label == 'unknown-contents' else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/poison-nova-necromancer/slots/Weapon/0',
                'third-parties/d2data/json/uniqueitems.json:/299',
            ),
        )


CASES = tuple(cases())
