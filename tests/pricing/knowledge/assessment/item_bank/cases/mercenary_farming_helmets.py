"""Actual Ist/Lem children and guide-specific farming mercenary helmets."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


STEALSKULL = Item(
    'Casque',
    'unique',
    'Stealskull',
    ((60, 0, 5), (62, 0, 5), (99, 0, 10), (93, 0, 10), (16, 0, 200), (80, 0, 55)),
    sockets=1,
    socket_contents='filled',
    socket_items=(SocketItem('Ist Rune'),),
)
CROWN = Item(
    'Corona',
    'unique',
    'Crown of Thieves',
    ((60, 0, 9), (79, 0, 130), (16, 0, 160), (39, 0, 33), (2, 0, 25)),
    sockets=1,
    socket_contents='filled',
    socket_items=(SocketItem('Lem Rune'),),
)


def specs():
    for prefix, build, klass, merc in (
        ('hammer', 'blessed-hammer-paladin', 'Paladin', 'Act 2 Holy Freeze'),
        ('blizzard', 'blizzard-sorceress', 'Sorceress', 'Act 2 Might'),
        ('meteor', 'meteor-sorceress', 'Sorceress', 'Act 2 Might'),
    ):
        yield (
            prefix + '-mf-stealskull-merc',
            STEALSKULL,
            klass,
            merc,
            'Ist Rune',
            (60, 93, 80),
            f'/{build}/variants/2/merc/Helmet',
            203,
        )
    for index, variant in enumerate(('standard', 'war-cry', 'whirlwind', 'leap-only'), 1):
        yield (
            'gold-find-' + variant + '-crown-merc',
            CROWN,
            'Barbarian',
            'Act 2 Might',
            'Lem Rune',
            (60, 79),
            f'/gold-find-barbarian/variants/{index}/merc/Helmet',
            206,
        )


def cases():
    for role, item, klass, merc, rune, priorities, source, native_id in specs():
        context = {'player_class': klass, 'mercenary_type': merc}
        examples = [
            ('minimum-native-rolls', item, context, 'positive', None),
            ('ethereal', replace(item, ethereal=True), context, 'positive', None),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'positive', None),
            ('wrong-mercenary', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'negative', 'merc'),
            ('unknown-mercenary', item, {'player_class': klass}, 'unknown', 'merc'),
            ('wrong-rune', replace(item, socket_items=(SocketItem('Ral Rune'),)), context, 'negative', 'socket'),
            ('unread-rune', replace(item, socket_items=()), context, 'unknown', 'socket'),
            ('empty-socket', replace(item, socket_contents='empty', socket_items=()), context, 'negative', 'socket'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown', 'socket'),
        ]
        if native_id == 203:
            examples.append(('upgraded', replace(item, base='Armet'), context, 'positive', None))
        else:
            examples.append(('not-upgraded', replace(item, base='Grand Crown'), context, 'negative', 'base'))
        config = role + '-stats'
        for label, observed, ctx, scenario, failed in examples:
            truth = 'unknown' if scenario == 'unknown' else 'false'
            dependencies = [
                IsPartialDict(label='Mercenary type: ' + merc, status=truth if failed == 'merc' else 'true')
            ]
            if native_id == 206:
                dependencies.append(
                    IsPartialDict(label='Cited upgraded Corona base', status='false' if failed == 'base' else 'true')
                )
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        side='merc',
                        rule_trace=IsPartialDict(truth='true'),
                        dependencies=dependencies,
                        socket_requirement=IsPartialDict(item=rune, confirmed=failed != 'socket'),
                    )
                ),
                'trade_tier': IsPartialDict(status='reviewed'),
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {f'{stat}:0': IsPartialDict(configuration_ids=Contains(config)) for stat in priorities}
                    )
                )
            yield Case(
                id=f'merc-farming-helmet/{role}/{label}',
                item=observed,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations={'62:0': (config,), '16:0': (config,)},
                report_contains=(item.name, 'Trade tier:', '200-240' if native_id == 203 else '160-200'),
                evidence=(
                    'pricing/data/wp-a-builds.json:' + source,
                    f'third-parties/d2data/json/uniqueitems.json:/{native_id}',
                    'third-parties/d2data/json/gems.json:/' + ('r24' if native_id == 203 else 'r20'),
                ),
            )


CASES = tuple(cases())
