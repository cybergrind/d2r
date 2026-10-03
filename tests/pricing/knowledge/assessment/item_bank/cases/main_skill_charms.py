"""Native table examples for four classes; expectations independent of rule JSON."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.charm_report_contracts import lightning_plain
from tests.pricing.knowledge.assessment.item_bank.fixed_charm_report_contracts import fixed_charm_checks
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item
from tests.pricing.knowledge.assessment.item_bank.vita_report_contracts import vita_checks


def cases():
    for build, klass, layer, prefix, wrong_layer, wrong_prefix, suffixes in (
        ('lightning-sentry-assassin', 'Assassin', 48, 502, 49, 503, ('vita',)),
        ('lightning-sorceress', 'Sorceress', 9, 443, 8, 442, ('vita', 'balance', 'plain')),
        ('lightning-strike-amazon', 'Amazon', 2, 432, 0, 430, ('vita', 'balance', 'inertia', 'plain')),
        ('poison-nova-necromancer', 'Necromancer', 17, 455, 18, 456, ('vita', 'balance', 'plain')),
    ):
        for index, suffix in enumerate(suffixes):
            role = f'{build}-main-skiller-{suffix}'
            config = role + '-stats'
            secondary = {'vita': ((7, 0, 36 * 256),), 'balance': ((99, 0, 12),), 'inertia': ((96, 0, 7),), 'plain': ()}[
                suffix
            ]
            suffix_ids = (
                () if suffix == 'plain' else (('suffix', {'vita': 338, 'balance': 265, 'inertia': 399}[suffix]),)
            )
            original = Item(
                'Grand Charm',
                'magic',
                raw_stats=((188, layer, 1), *secondary),
                affix_records=(('prefix', prefix), *suffix_ids),
                complete=True,
            )
            context = {'player_class': klass}
            variants = [
                ('minimum', original, context, 'true'),
                ('wrong-class', original, {'player_class': 'Druid'}, 'false'),
                ('unknown-class', original, {}, 'unknown'),
                (
                    'wrong-tree',
                    replace(
                        original,
                        raw_stats=((188, wrong_layer, 1), *secondary),
                        affix_records=(('prefix', wrong_prefix), *suffix_ids),
                    ),
                    context,
                    'false',
                ),
                ('absent-tree', replace(original, raw_stats=secondary, affix_records=suffix_ids), context, 'false'),
                ('unread-tree', replace(original, raw_stats=secondary, complete=False), context, 'unknown'),
                ('unidentified', replace(original, identified=False), context, 'false'),
            ]
            if secondary:
                variants += [
                    (
                        'absent-secondary',
                        replace(original, raw_stats=((188, layer, 1),), affix_records=(('prefix', prefix),)),
                        context,
                        'false',
                    ),
                    (
                        'unread-secondary',
                        replace(original, raw_stats=((188, layer, 1),), complete=False),
                        context,
                        'unknown',
                    ),
                ]
            if suffix == 'vita':
                for life, source in ((5, 332), (13, 333), (14, 333), (35, 337), (40, 338), (41, 339), (45, 339)):
                    variants.append(
                        (
                            f'life-{life}',
                            replace(
                                original,
                                raw_stats=((188, layer, 1), (7, 0, life * 256)),
                                affix_records=(('prefix', prefix), ('suffix', source)),
                            ),
                            context,
                            'false' if life < 36 else 'true',
                        )
                    )
            if suffix == 'plain':
                variants.append(
                    (
                        'optional-life',
                        replace(
                            original,
                            raw_stats=((188, layer, 1), (7, 0, 20 * 256)),
                            affix_records=(('prefix', prefix), ('suffix', 334)),
                        ),
                        context,
                        'true',
                    )
                )
            for label, item, ctx, truth in variants:
                active = truth == 'true'
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if active:
                    keys = (f'188:{layer}', *(f'{s}:{p}' for s, p, _ in secondary))
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict({k: IsPartialDict(configuration_ids=Contains(config)) for k in keys})
                    )
                yield Case(
                    id=f'main-skill-charms/{build}/{suffix}/{label}',
                    item=item,
                    context=ctx,
                    covers=(role,),
                    report_checks=lightning_plain(truth)
                    if build == 'lightning-sorceress'
                    and suffix == 'plain'
                    and label in {'minimum', 'wrong-class', 'unknown-class'}
                    else vita_checks(build, next(v // 256 for stat, _, v in item.raw_stats if stat == 7), truth)
                    if suffix == 'vita' and (label in {'minimum', 'unknown-class'} or label.startswith('life-'))
                    else fixed_charm_checks(build, suffix, truth)
                    if suffix != 'vita' and label in {'minimum', 'wrong-class', 'unknown-class'}
                    else None,
                    scenario='positive' if active else 'negative' if truth == 'false' else 'unknown',
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if active else (config,),
                    report_contains={
                        'vita': ('(5-45)', 'to Life', 'T1: 41-45'),
                        'balance': ('+12% (12-12%) Faster Hit Recovery [T1',),
                        'inertia': ('+7% (7-7%) Faster Run/Walk [T1',),
                        'plain': (),
                    }[suffix]
                    if active
                    else (),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/slots/Charms/{index}',
                        f'third-parties/d2data/json/magicprefix.json:/{prefix}',
                    ),
                )


CASES = tuple(cases())
