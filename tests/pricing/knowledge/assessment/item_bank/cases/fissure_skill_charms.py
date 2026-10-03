"""Independently authored native Elemental skiller examples and near misses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.fixed_charm_report_contracts import fixed_charm_checks
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item
from tests.pricing.knowledge.assessment.item_bank.vita_report_contracts import vita_checks


def cases():
    context = {'player_class': 'Druid'}
    for suffix, secondary, index in (
        ('vita', ((7, 0, 36 * 256),), 0),
        ('balance', ((99, 0, 12),), 1),
        ('inertia', ((96, 0, 7),), 2),
        ('plain', (), 3),
    ):
        role = 'fissure-elemental-grand-charm-' + suffix
        config = role + '-stats'
        suffix_records = (
            () if suffix == 'plain' else (('suffix', {'vita': 338, 'balance': 265, 'inertia': 399}[suffix]),)
        )
        original = Item(
            'Grand Charm',
            'magic',
            raw_stats=((188, 42, 1), *secondary),
            affix_records=(('prefix', 492), *suffix_records),
        )
        variants = [
            ('minimum', original, context, 'true'),
            ('wrong-class', original, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', original, {}, 'unknown'),
            (
                'summoning-tree',
                replace(
                    original,
                    raw_stats=((188, 40, 1), *secondary),
                    complete=True,
                    affix_records=(('prefix', 490), *suffix_records),
                ),
                context,
                'false',
            ),
            ('unread-tree', replace(original, raw_stats=secondary), context, 'unknown'),
            (
                'absent-tree',
                replace(original, raw_stats=secondary, complete=True, affix_records=suffix_records),
                context,
                'false',
            ),
            ('unidentified', replace(original, identified=False), context, 'false'),
        ]
        if secondary:
            variants.extend(
                (
                    ('unread-secondary', replace(original, raw_stats=((188, 42, 1),)), context, 'unknown'),
                    (
                        'absent-secondary',
                        replace(original, raw_stats=((188, 42, 1),), complete=True, affix_records=(('prefix', 492),)),
                        context,
                        'false',
                    ),
                )
            )
        if suffix == 'vita':
            for life, source in ((5, 332), (13, 333), (14, 333), (35, 337), (40, 338), (41, 339), (45, 339)):
                variants.append(
                    (
                        f'life-{life}',
                        replace(
                            original,
                            raw_stats=((188, 42, 1), (7, 0, life * 256)),
                            affix_records=(
                                ('prefix', 492),
                                ('suffix', source),
                            ),
                        ),
                        context,
                        'false' if life < 36 else 'true',
                    )
                )
        elif suffix == 'plain':
            variants.append(
                (
                    'optional-life',
                    replace(
                        original,
                        raw_stats=((188, 42, 1), (7, 0, 20 * 256)),
                        affix_records=(('prefix', 492), ('suffix', 334)),
                    ),
                    context,
                    'true',
                )
            )
        for label, item, ctx, truth in variants:
            active = truth == 'true'
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            keys = ('188:42', *(f'{s}:{p}' for s, p, _ in secondary))
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({k: IsPartialDict(configuration_ids=Contains(config)) for k in keys})
                )
            yield Case(
                id=f'fissure-skill-charms/{suffix}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                report_checks=vita_checks(
                    'fissure-druid', next(v // 256 for stat, _, v in item.raw_stats if stat == 7), truth, role_id=role
                )
                if suffix == 'vita' and (label in {'minimum', 'unknown-class'} or label.startswith('life-'))
                else fixed_charm_checks('fissure-druid', suffix, truth, role_id=role)
                if suffix != 'vita' and label in {'minimum', 'wrong-class', 'unknown-class'}
                else None,
                scenario='positive' if active else 'negative' if truth == 'false' else 'unknown',
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if active else (config,),
                report_contains=(
                    'Elemental Skills',
                    *(
                        {
                            'vita': ('to Life', '(5-45)', 'T1: 41-45'),
                            'balance': ('+12% (12-12%) Faster Hit Recovery [T1',),
                            'inertia': ('+7% (7-7%) Faster Run/Walk [T1',),
                            'plain': (),
                        }[suffix]
                    ),
                )
                if active
                else (),
                evidence=(
                    f'pricing/data/wp-a-builds.json:/fissure-druid/slots/Charms/{index}',
                    'third-parties/d2data/json/magicprefix.json:/492',
                ),
            )


CASES = tuple(cases())
