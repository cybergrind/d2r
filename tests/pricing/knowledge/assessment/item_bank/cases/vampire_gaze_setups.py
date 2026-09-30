"""Distinct reviewed Rogue/Frenzy helmet setups, not generic mercenary demand."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


BASE = Item(
    'Grim Helm',
    'unique',
    'Vampire Gaze',
    ((60, 0, 6), (62, 0, 6), (36, 0, 15), (35, 0, 10), (16, 0, 100), (54, 0, 6), (55, 0, 22), (56, 0, 100)),
)
RES = tuple((stat, 0, 15) for stat in (39, 41, 43, 45))
JEWEL = SocketItem('Jewel', ((93, 0, 15), *RES), complete=True)
SPECS = (
    ('dream-hybrid-gaze-merc', 'Paladin', '/dream-paladin/variants/1/merc', 'jewel'),
    ('dream-ubers-gaze-merc', 'Paladin', '/dream-paladin/variants/2/merc', 'jewel'),
    ('lightning-strike-standard-gaze-merc', 'Amazon', '/lightning-strike-amazon/variants/1/merc', 'jewel'),
    ('lightning-strike-ubers-gaze-merc', 'Amazon', '/lightning-strike-amazon/variants/2/merc', 'native'),
    ('lightning-fury-ubers-gaze-merc', 'Amazon', '/lightning-fury-amazon-guide/variants/3/merc', 'um'),
)


def cases():
    for role, klass, source, payload in SPECS:
        merc = 'Act 1 Cold' if payload == 'jewel' else 'Act 5 Frenzy'
        context = {'player_class': klass, 'mercenary_type': merc}
        item = (
            BASE
            if payload == 'native'
            else replace(
                BASE,
                sockets=1,
                socket_contents='filled',
                socket_items=(JEWEL if payload == 'jewel' else SocketItem('Um Rune'),),
                raw_stats=(*BASE.raw_stats, *RES, *(((93, 0, 15),) if payload == 'jewel' else ()), (194, 0, 1)),
            )
        )
        examples = [
            ('minimum-native-rolls', item, context, 'positive', 'true', 'true', None),
            ('ethereal', replace(item, ethereal=True), context, 'positive', 'true', 'true', None),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'positive', 'true', 'true', None),
            ('upgraded', replace(item, base='Bone Visage'), context, 'positive', 'true', 'true', None),
            ('wrong-mercenary', item, {**context, 'mercenary_type': 'Act 2 Might'}, 'negative', 'true', 'false', None),
            ('unknown-mercenary', item, {'player_class': klass}, 'unknown', 'true', 'unknown', None),
        ]
        for key, label in ((60, 'unread-life-leech'), (36, 'unread-physical-reduction')):
            examples.append(
                (
                    label,
                    replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != key)),
                    context,
                    'unknown',
                    'unknown',
                    'true',
                    None,
                )
            )
        if payload != 'native':
            for label, candidate, scenario, child in (
                ('wrong-rune', replace(item, socket_items=(SocketItem('Ral Rune'),)), 'negative', 'false'),
                ('unread-child', replace(item, socket_items=()), 'unknown', 'unknown'),
                ('empty-socket', replace(item, socket_contents='empty', socket_items=()), 'negative', 'false'),
            ):
                examples.append((label, candidate, context, scenario, 'true', 'true', child))
        if payload == 'jewel':
            # These cases check the cited 15/15 setup. Failing it does not make a lesser jewel worthless.
            for label, child, scenario, truth in (
                ('ias-only', SocketItem('Jewel', ((93, 0, 15),), complete=True), 'negative', 'false'),
                ('resistance-only', SocketItem('Jewel', RES, complete=True), 'negative', 'false'),
                ('unread-jewel-stats', replace(JEWEL, complete=False), 'unknown', 'unknown'),
                (
                    'one-resistance-below-setup',
                    SocketItem('Jewel', ((93, 0, 15), *RES[:-1], (45, 0, 14)), complete=True),
                    'negative',
                    'false',
                ),
            ):
                examples.append((label, replace(item, socket_items=(child,)), context, scenario, 'true', 'true', truth))
        for label, candidate, ctx, scenario, required, bearer, child in examples:
            config = role + '-stats'
            expected_role = {
                'id': role,
                'side': 'merc',
                'status': 'partial',
                'rule_trace': IsPartialDict(truth=required),
                'dependencies': Contains(IsPartialDict(label='Mercenary type: ' + merc, status=bearer)),
            }
            if payload == 'jewel':
                expected_role['dependencies'] = Contains(
                    IsPartialDict(label='Mercenary type: ' + merc, status=bearer),
                    IsPartialDict(
                        label='One socket jewel with 15% IAS and 15% to each elemental resistance',
                        status=child or 'true',
                    ),
                )
            elif payload == 'um':
                expected_role['socket_requirement'] = IsPartialDict(item='Um Rune', confirmed=child is None)
            expected = {'roles': Contains(IsPartialDict(**expected_role))}
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(config)) for key in ('60:0', '36:0')}
                    )
                )
            yield Case(
                id=f'vampire-gaze-setups/{role}/{label}',
                item=candidate,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                absent_stat_configurations={'62:0': (config,), '16:0': (config,)},
                report_contains=('Vampire Gaze', 'Trade tier:'),
                evidence=('pricing/data/wp-a-builds.json:' + source, 'third-parties/d2data/json/uniqueitems.json:/208'),
            )


CASES = tuple(cases())
