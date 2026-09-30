"""Explicit FOH gear alternatives require actual armor Topazes and their effect."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


def cases():
    for slug, base, count in (('mask', 'Mask', 3), ('gothic-plate', 'Gothic Plate', 4)):
        role = f'fist-of-the-heavens-paladin-{slug}-topaz-find'
        for quality in ('normal', 'superior'):
            item = Item(
                base,
                quality,
                raw_stats=((80, 0, count * 24), (194, 0, count)),
                sockets=count,
                socket_contents='filled',
                socket_items=(SocketItem('Perfect Topaz'),) * count,
            )
            for label, candidate, klass, scenario in (
                ('native', item, 'Paladin', 'positive'),
                (
                    'wrong-gems',
                    replace(item, socket_items=(SocketItem('Perfect Ruby'),) * count),
                    'Paladin',
                    'negative',
                ),
                ('empty', replace(item, socket_contents='empty', socket_items=()), 'Paladin', 'negative'),
                ('unread-gems', replace(item, socket_items=()), 'Paladin', 'unknown'),
                (
                    'short-mf',
                    replace(item, raw_stats=((80, 0, count * 24 - 1), (194, 0, count))),
                    'Paladin',
                    'negative',
                ),
                ('ethereal', replace(item, ethereal=True), 'Paladin', 'negative'),
                ('unknown-ethereal', replace(item, ethereal=None), 'Paladin', 'unknown'),
                ('wrong-class', item, 'Amazon', 'negative'),
                ('unknown-class', item, None, 'unknown'),
                ('magic', replace(item, rarity='magic'), 'Paladin', 'negative'),
            ):
                expected = {}
                if scenario == 'positive':
                    expected = {
                        'assessment': IsPartialDict(
                            stat_evaluation=IsPartialDict(
                                annotations=IsPartialDict(
                                    {'80:0': IsPartialDict(configuration_ids=Contains(role + '-stats'))}
                                )
                            )
                        )
                    }
                elif label in ('wrong-gems', 'empty', 'short-mf'):
                    expected = {'assessment': IsPartialDict(roles=Contains(IsPartialDict(id=role, status='failed')))}
                yield Case(
                    id=f'foh-topaz/{slug}/{quality}/{label}',
                    item=candidate,
                    context={'player_class': klass} if klass else {},
                    covers=(f'role:{role}:{quality}',),
                    scenario=scenario,
                    expected=expected,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(f'Sockets: {count}', 'Perfect Topaz') if scenario == 'positive' else (),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__fist-of-the-heavens-paladin.html/sections/34',
                    ),
                )


CASES = tuple(cases())
