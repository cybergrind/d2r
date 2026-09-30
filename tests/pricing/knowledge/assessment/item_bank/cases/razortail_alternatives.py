"""Razortail guide alternatives preserve class, upgraded base and known facts."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    ('double-throw-barbarian-guide', 'Barbarian'),
    ('enchant-sorceress', 'Sorceress'),
    ('lightning-fury-amazon-guide', 'Amazon'),
    ('strafe-amazon', 'Amazon'),
)


def cases():
    item = Item(
        'Sharkskin Belt',
        'unique',
        'Razortail',
        raw_stats=((156, 0, 33), (2, 0, 15), (22, 0, 10), (16, 0, 135), (31, 0, 15)),
    )
    for guide, player_class in USES:
        role = guide + '-razortail-boots-belts-alternative'
        context = {'player_class': player_class}
        for label, candidate, loadout, truth, scenario in (
            ('native', item, context, 'true', 'positive'),
            ('upgraded', replace(item, base='Vampirefang Belt'), context, 'true', 'positive'),
            ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
            ('wrong-class', item, {'player_class': 'Necromancer'}, 'false', 'negative'),
            ('unread-class', item, {}, 'unknown', 'unknown'),
            ('impossible-ethereal', replace(item, ethereal=True), context, 'false', 'negative'),
            ('unread-ethereal', replace(item, ethereal=None), context, 'unknown', 'unknown'),
            ('impossible-sockets', replace(item, sockets=1), context, 'false', 'negative'),
            ('unread-sockets', replace(item, sockets=None), context, 'unknown', 'unknown'),
        ):
            yield Case(
                id=f'razortail-alternative/{guide}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=(role,),
                expected={
                    'assessment': IsPartialDict(
                        roles=Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))
                    )
                },
                report_contains=('Razortail',),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{guide}/slots/Belts/0',
                    'third-parties/d2data/json/uniqueitems.json:/243',
                ),
            )


CASES = tuple(cases())
