"""Native MF charm swap: explicit high-player activity, correct tree and Vita rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item
from tests.pricing.knowledge.assessment.item_bank.vita_report_contracts import vita_checks


ROLE = 'lightning-sentry-assassin-mf-high-player-skiller'
LABEL = 'High-player-count farming; replace Magic Find small charms for damage'


def cases():
    original = Item(
        'Grand Charm',
        'magic',
        raw_stats=((188, 48, 1), (7, 0, 36 * 256)),
        affix_records=(('prefix', 502), ('suffix', 338)),
        complete=True,
    )
    context = {'player_class': 'Assassin', 'activity': 'high_player_count_farming'}
    variants = [
        ('minimum', original, context, 'true', 'true'),
        ('solo', original, {**context, 'activity': 'solo_farming'}, 'false', 'false'),
        ('unknown-activity', original, {'player_class': 'Assassin'}, 'unknown', 'unknown'),
        ('wrong-class', original, {**context, 'player_class': 'Druid'}, 'false', 'true'),
        ('unknown-class', original, {'activity': context['activity']}, 'unknown', 'true'),
        (
            'wrong-tree',
            replace(
                original, raw_stats=((188, 49, 1), (7, 0, 36 * 256)), affix_records=(('prefix', 503), ('suffix', 338))
            ),
            context,
            'false',
            'true',
        ),
        ('unread-life', replace(original, raw_stats=((188, 48, 1),), complete=False), context, 'unknown', 'true'),
        (
            'absent-life',
            replace(original, raw_stats=((188, 48, 1),), affix_records=(('prefix', 502),)),
            context,
            'false',
            'true',
        ),
        ('unidentified', replace(original, identified=False), context, 'false', 'true'),
    ]
    for life, suffix in ((5, 332), (13, 333), (14, 333), (35, 337), (40, 338), (41, 339), (45, 339)):
        variants.append(
            (
                f'life-{life}',
                replace(
                    original,
                    raw_stats=((188, 48, 1), (7, 0, life * 256)),
                    affix_records=(('prefix', 502), ('suffix', suffix)),
                ),
                context,
                'true' if life >= 36 else 'false',
                'true',
            )
        )
    for label, item, ctx, truth, dependency in variants:
        annotated = label in {
            'minimum',
            'solo',
            'unknown-activity',
            'wrong-class',
            'unknown-class',
        } or label.startswith('life-')
        checks = (
            vita_checks(
                'lightning-sentry-assassin', next(v // 256 for s, _, v in item.raw_stats if s == 7), truth, role_id=ROLE
            )
            if annotated
            else None
        )
        yield Case(
            id=f'sentry-high-player-charm/{label}',
            item=item,
            context=ctx,
            covers=(ROLE,),
            scenario='positive' if truth == 'true' else 'negative' if truth == 'false' else 'unknown',
            expected={
                'assessment': IsPartialDict(
                    roles=Contains(
                        IsPartialDict(
                            id=ROLE,
                            variant='Magic Find',
                            rule_trace=IsPartialDict(truth=truth),
                            dependencies=Contains(IsPartialDict(label=LABEL, status=dependency)),
                        )
                    )
                )
            },
            absent_configurations=() if truth == 'true' else (ROLE + '-stats',),
            report_checks=checks,
            detail_contains=(({'true': 'Setup: ', 'false': 'Needs: ', 'unknown': 'Check: '}[dependency] + LABEL),)
            if label in {'minimum', 'solo', 'unknown-activity'}
            else (),
            evidence=(
                'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__lightning-sentry-assassin.html/sections/20/text',
                'third-parties/d2data/json/magicprefix.json:/502',
                'third-parties/d2data/json/magicsuffix.json:/338',
            ),
        )


CASES = tuple(cases())
