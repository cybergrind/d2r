"""Valuable CBF belt: native utility survives the cited capacity upgrade."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BELT = Item('Sash', 'set', "Death's Guard", ((153, 0, 1),), named_table_id=48)


def cases():
    for build, klass in (('strafe-amazon', 'Amazon'), ('double-throw-barbarian-guide', 'Barbarian')):
        role = build + '-deaths-guard-upgrade'
        config = role + '-stats'
        context = {'player_class': klass}
        upgraded = replace(BELT, base='Demonhide Sash')
        for label, item, ctx, truth, ready in (
            ('native-cbf', BELT, context, 'true', False),
            ('upgraded-capacity', upgraded, context, 'true', True),
            ('no-set-companion-needed', upgraded, {**context, 'player_items': []}, 'true', True),
            ('wrong-class', upgraded, {'player_class': 'Necromancer'}, 'false', False),
            ('unknown-class', upgraded, {}, 'unknown', False),
            ('missing-cbf', replace(upgraded, raw_stats=(), complete=True), context, 'false', False),
            ('unread-cbf', replace(upgraded, raw_stats=()), context, 'unknown', False),
            ('unidentified', replace(upgraded, identified=False), context, 'unknown', False),
        ):
            role_expectation = {'id': role, 'rule_trace': IsPartialDict(truth=truth)}
            if label == 'unidentified':
                # Identification gates the whole role; observed stat predicates alone can still pass.
                role_expectation = {'id': role, 'status': 'unknown'}
            if label == 'native-cbf':
                role_expectation['dependencies'] = Contains(
                    IsPartialDict(
                        status='false',
                        preparation=IsPartialDict(target_name='Demonhide Sash'),
                    )
                )
            elif ready:
                role_expectation['dependencies'] = Contains(IsPartialDict(status='true'))
            expected = {'roles': Contains(IsPartialDict(**role_expectation))}
            if ready:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({'153:0': IsPartialDict(configuration_ids=Contains(config))})
                )
            yield Case(
                id=f'deaths-guard-upgrade/{build}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario='positive' if truth == 'true' else 'unknown' if truth == 'unknown' else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if ready else (config,),
                absent_stat_configurations=dict.fromkeys(('39:0', '41:0', '43:0', '45:0', '93:0'), (config,)),
                report_contains=("Death's Guard", 'Cannot Be Frozen', 'Leveling: high') if truth == 'true' else (),
                evidence=(
                    f'pricing/data/wp-a-variants/{build}.json:/variants/0',
                    "third-parties/d2data/json/setitems.json:/Death's Guard",
                    'third-parties/d2data/json/armor.json:/lbl',
                    'third-parties/d2data/json/armor.json:/zlb',
                ),
            )


CASES = tuple(cases())
