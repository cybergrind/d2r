"""Independent native Arreat and legal magic/rare 2/20 Berserk alternatives."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def emit(slug, item, context, truth, keys, label):
    role = 'berserk-barbarian-' + slug
    config = role + '-stats'
    expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
    if truth == 'true':
        expected['stat_evaluation'] = IsPartialDict(
            annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
        )
    return Case(
        id=f'berserk/helm-alternatives/{slug}/{item.rarity}/{label}',
        item=item,
        context=context,
        expected={'assessment': IsPartialDict(**expected)},
        covers=(role,),
        scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
        absent_configurations=() if truth == 'true' else (config,),
        absent_stat_configurations={'60:0': (config,)},
        evidence=(
            'pricing/data/wp-a-builds.json',
            'third-parties/d2data/json/uniqueitems.json',
            'third-parties/d2data/json/magicprefix.json',
            'third-parties/d2data/json/magicsuffix.json',
        ),
    )


def cases():
    context = {'player_class': 'Barbarian'}
    stats = (
        (83, 4, 2),
        (188, 32, 2),
        (16, 0, 150),
        (99, 0, 30),
        (119, 0, 20),
        (0, 0, 20),
        (2, 0, 20),
        (60, 0, 3),
        *((s, 0, 30) for s in (39, 41, 43, 45)),
    )
    item = Item('Slayer Guard', 'unique', "Arreat's Face", stats)
    keys = ('83:4', '188:32', '99:0', '119:0', '0:0', '2:0', '39:0', '41:0', '43:0', '45:0')
    for label, candidate, loadout, truth in (
        ('minimum', item, context, 'true'),
        (
            'maximum',
            replace(item, raw_stats=tuple((s, layer, {16: 200, 60: 6}.get(s, v)) for s, layer, v in stats)),
            context,
            'true',
        ),
        ('upgraded', replace(item, base='Guardian Crown'), context, 'true'),
        ('empty-socket', replace(item, sockets=1), context, 'true'),
        ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        ('invalid-sockets', replace(item, sockets=2), context, 'false'),
        ('ethereal', replace(item, ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
        ('unidentified', replace(item, identified=False), context, 'false'),
        ('wrong-class', item, {'player_class': 'Paladin'}, 'false'),
        ('unknown-class', item, {}, 'unknown'),
    ):
        yield emit('arreat-s-face-equipment-tail-alternative', candidate, loadout, truth, keys, label)
    for quality in ('magic', 'rare'):
        item = Item('Diadem', quality, raw_stats=((83, 4, 2), (105, 0, 20)))
        for label, candidate, loadout, truth in (
            ('native', item, context, 'true'),
            ('circlet', replace(item, base='Circlet'), context, 'true'),
            ('socketed', replace(item, sockets=2), context, 'true'),
            ('unknown-sockets', replace(item, sockets=None), context, 'true'),
            ('one-skill', replace(item, raw_stats=((83, 4, 1), (105, 0, 20))), context, 'false'),
            ('ten-fcr', replace(item, raw_stats=((83, 4, 2), (105, 0, 10))), context, 'false'),
            ('unread-fcr', replace(item, raw_stats=((83, 4, 2),)), context, 'unknown'),
            ('unread-skills', replace(item, raw_stats=((105, 0, 20),)), context, 'unknown'),
            ('no-fcr', replace(item, raw_stats=((83, 4, 2),), complete=True), context, 'false'),
            ('wrong-skill', replace(item, raw_stats=((83, 1, 2), (105, 0, 20)), complete=True), context, 'false'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        ):
            yield emit('berserker-magus', candidate, loadout, truth, ('83:4', '105:0'), label)


CASES = tuple(cases())
