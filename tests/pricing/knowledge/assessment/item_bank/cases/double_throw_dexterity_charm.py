"""Independent Sharp/Dexterity native rolls, not a perfect planner clone."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'double-throw-sharp-dexterity-grand-charm'
CONFIG = ROLE + '-stats'
RAW = ((19, 0, 49), (22, 0, 7), (2, 0, 3))
ITEM = Item('Grand Charm', 'magic', raw_stats=RAW)


def cases():
    context = {'player_class': 'Barbarian'}
    rows = [
        ('lower-dexterity-tier', ITEM, context, 'true'),
        ('higher-dexterity-tier', replace(ITEM, raw_stats=(*RAW[:2], (2, 0, 5))), context, 'true'),
        ('planner-maxima', replace(ITEM, raw_stats=((19, 0, 76), (22, 0, 10), (2, 0, 6))), context, 'true'),
        ('wrong-class', ITEM, {'player_class': 'Paladin'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('ethereal', replace(ITEM, ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
        ('unidentified', replace(ITEM, identified=False), context, 'false'),
        ('illegal-socket', replace(ITEM, sockets=1, raw_stats=(*RAW, (194, 0, 1))), context, 'false'),
    ]
    for stat in (19, 22, 2):
        raw = tuple(r for r in RAW if r[0] != stat)
        rows.extend(
            (
                (f'absent-{stat}', replace(ITEM, raw_stats=raw, complete=True), context, 'false'),
                (f'unread-{stat}', replace(ITEM, raw_stats=raw), context, 'unknown'),
            )
        )
    for label, item, ctx, truth in rows:
        active = truth == 'true'
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if active:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(CONFIG)) for key in ('19:0', '22:0', '2:0')}
                )
            )
        yield Case(
            id='double-throw-dexterity-charm/' + label,
            item=item,
            context=ctx,
            covers=(ROLE,),
            scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if active else (CONFIG,),
            detail_contains=('Both native Dexterity tiers qualify; the perfect planner roll is not required.',)
            if active
            else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/double-throw-barbarian-guide/slots/Charms/13',
                'pricing/raw/mr/planners/db0106mf.json:/data/items/140',
                'third-parties/d2data/json/magicprefix.json:/253',
                'third-parties/d2data/json/magicsuffix.json:/255',
                'third-parties/d2data/json/magicsuffix.json:/258',
            ),
        )


CASES = tuple(cases())
