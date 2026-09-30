"""Guide Starter amulet core and optional stats, independently constructed."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'blessed-hammer-paladin-starter-rare-amulet'
ITEM = Item('Amulet', 'rare', 'Storm Torc', ((188, 24, 1), (105, 0, 10)))


def cases():
    context = {'player_class': 'Paladin'}
    extras = ((9, 0, 15 * 256), (39, 0, 20))
    rows = [
        ('core-only', ITEM, context, 'true', ('188:24', '105:0')),
        (
            'supporting-rolls',
            replace(ITEM, raw_stats=(*ITEM.raw_stats, *extras)),
            context,
            'true',
            ('188:24', '105:0', '9:0', '39:0'),
        ),
        ('two-skills', replace(ITEM, raw_stats=((188, 24, 2), (105, 0, 10))), context, 'true', ('188:24', '105:0')),
        ('below-fcr', replace(ITEM, raw_stats=((188, 24, 1), (105, 0, 9)), complete=True), context, 'false', ()),
        ('wrong-tab', replace(ITEM, raw_stats=((188, 25, 1), (105, 0, 10)), complete=True), context, 'false', ()),
        ('absent-skill', replace(ITEM, raw_stats=((105, 0, 10),), complete=True), context, 'false', ()),
        ('unread-skill', replace(ITEM, raw_stats=((105, 0, 10),)), context, 'unknown', ()),
        ('absent-fcr', replace(ITEM, raw_stats=((188, 24, 1),), complete=True), context, 'false', ()),
        ('unread-fcr', replace(ITEM, raw_stats=((188, 24, 1),)), context, 'unknown', ()),
        ('wrong-class', ITEM, {'player_class': 'Sorceress'}, 'false', ()),
        ('unknown-class', ITEM, {}, 'unknown', ()),
        ('unidentified', replace(ITEM, identified=False), context, 'false', ()),
        ('ethereal', replace(ITEM, ethereal=True), context, 'false', ()),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown', ()),
    ]
    for label, remaining in (('one-teleport-charge', 1), ('depleted-teleport', 0)):
        rows.append(
            (
                label,
                replace(ITEM, raw_stats=(*ITEM.raw_stats, *extras, (204, 3458, (25 << 8) | remaining))),
                context,
                'true',
                ('188:24', '105:0', '9:0', '39:0'),
            )
        )
    for label, item, loadout, truth, keys in rows:
        config = ROLE + '-stats'
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
            )
        yield Case(
            id=f'hammer/starter-amulet/{label}',
            item=item,
            context=loadout,
            expected={'assessment': IsPartialDict(**expected)},
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            absent_configurations=() if truth == 'true' else (config,),
            absent_stat_configurations={'204:3458': (config,), '97:54': (config,)},
            report_contains=('Amulet',),
            evidence=('pricing/data/wp-a-builds.json:/blessed-hammer-paladin/variants/0',),
        )


CASES = tuple(cases())
