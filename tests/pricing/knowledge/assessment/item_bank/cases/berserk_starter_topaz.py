"""Guide-specified Starter gem payloads; no inferred old-planner rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


def cases():
    for slug, base, count, mf in [('armor', 'Dusk Shroud', 4, 96), ('helmet', 'Crown', 3, 72)]:
        role = f'berserk-barbarian-starter-topaz-{slug}'
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                raw_stats=((80, 0, mf), (194, 0, count)),
                sockets=count,
                socket_contents='filled',
                socket_items=(SocketItem('Perfect Topaz'),) * count,
            )
            for label, candidate, klass, active in (
                ('native', item, 'Barbarian', True),
                ('ethereal', replace(item, ethereal=True), 'Barbarian', False),
                ('unknown-ethereal', replace(item, ethereal=None), 'Barbarian', False),
                ('unknown-class', item, None, False),
                ('wrong-class', item, 'Warlock', False),
                ('wrong-base', replace(item, base='Monarch'), 'Barbarian', False),
                ('wrong-gems', replace(item, socket_items=(SocketItem('Perfect Ruby'),) * count), 'Barbarian', False),
                ('missing-gem', replace(item, socket_items=item.socket_items[:-1]), 'Barbarian', False),
                ('short-mf', replace(item, raw_stats=((80, 0, mf - 1), (194, 0, count))), 'Barbarian', False),
                ('unidentified', replace(item, identified=False), 'Barbarian', False),
            ):
                yield Case(
                    id=f'berserk-starter-topaz/{slug}/{quality}/{label}',
                    item=candidate,
                    context={'player_class': klass},
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
                    report_contains=(f'Sockets: {count}', 'Perfect Topaz') if active else (),
                    evidence=(
                        'pricing/data/wp-a-builds.json:/berserk-barbarian/variants/0',
                        'third-parties/d2data/json/gems.json:Perfect Topaz armor effect',
                    ),
                )


CASES = tuple(cases())
