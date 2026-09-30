"""Native Astreon rolls: Combat skills benefit Hammer; weapon attack modifiers do not."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'blessed-hammer-paladin-astreon-s-iron-ward-attack-utility-alternative'
ITEM = Item(
    'Caduceus',
    'unique',
    "Astreon's Iron Ward",
    (
        (188, 24, 2),
        (34, 0, 4),
        (17, 0, 240),
        (18, 0, 240),
        (150, 0, 25),
        (119, 0, 150),
        (93, 0, 10),
        (52, 0, 80),
        (53, 0, 240),
        (111, 0, 40),
        (136, 0, 33),
    ),
)


def cases():
    context = {'player_class': 'Paladin'}
    maxima = {188: 4, 34: 7, 17: 290, 18: 290, 119: 200, 111: 85}
    for label, item, loadout, truth in (
        ('minimum', ITEM, context, 'true'),
        (
            'maximum',
            replace(ITEM, raw_stats=tuple((s, p, maxima.get(s, v)) for s, p, v in ITEM.raw_stats)),
            context,
            'true',
        ),
        ('ethereal-casting', replace(ITEM, ethereal=True), context, 'true'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'true'),
        ('empty-socket', replace(ITEM, sockets=1), context, 'true'),
        ('unknown-sockets', replace(ITEM, sockets=None), context, 'unknown'),
        ('invalid-sockets', replace(ITEM, sockets=2), context, 'false'),
        ('wrong-class', ITEM, {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('unidentified', replace(ITEM, identified=False), context, 'false'),
    ):
        config = ROLE + '-stats'
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(config)) for key in ('188:24', '34:0')}
                )
            )
        yield Case(
            id=f'hammer/astreon/{label}',
            item=item,
            context=loadout,
            expected={'assessment': IsPartialDict(**expected)},
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            absent_configurations=() if truth == 'true' else (config,),
            absent_stat_configurations=dict.fromkeys(
                ('17:0', '18:0', '150:0', '119:0', '93:0', '52:0', '53:0', '111:0', '136:0'), (config,)
            ),
            report_contains=(ITEM.name, 'Trade tier:') if truth == 'true' else ('Caduceus',),
            evidence=(
                'pricing/data/wp-a-builds.json:/blessed-hammer-paladin/slots/Weapon/3',
                'third-parties/d2data/json/uniqueitems.json:/380',
            ),
        )


CASES = tuple(cases())
