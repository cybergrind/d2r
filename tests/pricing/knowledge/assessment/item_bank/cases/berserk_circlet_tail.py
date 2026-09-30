"""Luck socket preparation and rare mobility candidates preserve secondary preferences."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def emit(role, label, item, context, truth, keys):
    expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
    if truth == 'true':
        expected['stat_evaluation'] = IsPartialDict(annotations=IsPartialDict({
            key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys
        }))
    return Case(
        id=f'berserk/circlet-tail/{role}/{label}', item=item, context=context,
        expected={'assessment': IsPartialDict(**expected)}, covers=(role,),
        scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
        absent_configurations=() if truth == 'true' else (role + '-stats',),
        evidence=('pricing/data/wp-a-builds.json', 'pricing/data/wp-a-variants/berserk-barbarian.json',
                  'third-parties/d2data/json/magicsuffix.json'),
    )


def cases():
    context = {'player_class': 'Barbarian'}
    item = Item('Tiara', 'magic', raw_stats=((80, 0, 26),), sockets=3)
    for label, candidate, loadout, truth in (
        ('minimum', item, context, 'true'),
        ('perfect-suffix', replace(item, raw_stats=((80, 0, 35),)), context, 'true'),
        ('lower-suffix', replace(item, raw_stats=((80, 0, 25),)), context, 'false'),
        ('unread-suffix', replace(item, raw_stats=()), context, 'unknown'),
        ('two-sockets', replace(item, sockets=2), context, 'false'),
        ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        ('filled', replace(item, socket_contents='filled'), context, 'false'),
        ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
        ('uncited-diadem', replace(item, base='Diadem'), context, 'false'),
        ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', item, {}, 'unknown'),
    ):
        yield emit('berserk-barbarian-luck-tiara-socket-base', label, candidate, loadout, truth, ('80:0',))
    item = Item('Diadem', 'rare', raw_stats=((83, 4, 2), (105, 0, 20)))
    for label, candidate, truth, keys in (
        ('core-only', item, 'true', ('83:4', '105:0')),
        ('life-sockets', replace(item, raw_stats=(*item.raw_stats, (7, 0, 40 * 256)), sockets=2),
         'true', ('83:4', '105:0', '7:0')),
        ('unknown-sockets', replace(item, sockets=None), 'true', ('83:4', '105:0')),
        ('one-skill', replace(item, raw_stats=((83, 4, 1), (105, 0, 20))), 'false', ()),
        ('ten-fcr', replace(item, raw_stats=((83, 4, 2), (105, 0, 10))), 'false', ()),
        ('unread-skills', replace(item, raw_stats=((105, 0, 20),)), 'unknown', ()),
        ('unread-fcr', replace(item, raw_stats=((83, 4, 2),)), 'unknown', ()),
        ('absent-fcr', replace(item, raw_stats=((83, 4, 2),), complete=True), 'false', ()),
    ):
        yield emit('berserk-mobility-circlet', label, candidate, context, truth, keys)


CASES = tuple(cases())
