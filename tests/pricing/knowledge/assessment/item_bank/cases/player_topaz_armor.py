"""Four linked armor Topazes, not a same-name mercenary resistance setup."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


BUILDS = (
    ('berserk-barbarian', 'Barbarian'),
    ('double-throw-barbarian-guide', 'Barbarian'),
    ('lightning-strike-amazon', 'Amazon'),
)


def cases():
    for build, klass in BUILDS:
        role = build + '-perfect-topaz-general-armor'
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                'Dusk Shroud',
                quality,
                raw_stats=((80, 0, 96), (194, 0, 4)),
                sockets=4,
                socket_contents='filled',
                socket_items=(SocketItem('Perfect Topaz'),) * 4,
            )
            for label, candidate, player, active in (
                ('native', item, klass, True),
                ('ethereal', replace(item, ethereal=True), klass, False),
                ('unknown-ethereal', replace(item, ethereal=None), klass, False),
                ('wrong-class', item, 'Warlock', False),
                ('wrong-base', replace(item, base='Monarch'), klass, False),
                ('wrong-gems', replace(item, socket_items=(SocketItem('Perfect Ruby'),) * 4), klass, False),
                ('missing-gem', replace(item, socket_items=item.socket_items[:3]), klass, False),
                ('short-mf', replace(item, raw_stats=((80, 0, 95), (194, 0, 4))), klass, False),
                ('unidentified', replace(item, identified=False), klass, False),
            ):
                yield Case(
                    id=f'player-topaz-armor/{build}/{quality}/{label}',
                    item=candidate,
                    context={'player_class': player},
                    covers=(role,),
                    scenario='positive' if active else 'unknown' if label.startswith('unknown') else 'negative',
                    expected={
                        'assessment': IsPartialDict(
                            stat_evaluation=IsPartialDict(
                                annotations=IsPartialDict(
                                    {'80:0': IsPartialDict(configuration_ids=Contains(role + '-stats'))}
                                )
                            )
                        )
                    }
                    if active
                    else {'assessment': IsPartialDict(roles=Contains(IsPartialDict(id=role, status='failed')))}
                    if label == 'wrong-gems'
                    else {},
                    absent_configurations=() if active else (role + '-stats',),
                    report_contains=('Sockets: 4', 'Perfect Topaz') if active else (),
                    evidence=(f'pricing/raw/mr/guides__{build}.html:Gear Options / Body Armor',),
                )


CASES = tuple(cases())
