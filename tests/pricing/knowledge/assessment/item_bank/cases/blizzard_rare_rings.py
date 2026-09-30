"""Blizzard MF/set rings: six legal affixes, support rolls and incomplete captures."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLES = ('blizzard-mf-ring', 'blizzard-set-ring')
CONFIGS = tuple(role + '-stats' for role in ROLES)
RESISTS = (39, 41, 43, 45)


def ring(element, *, perfect=True):
    resistance, extra, life, mf = (11, 30, 40, 25) if perfect else (8, 21, 31, 10)
    return Item(
        'Ring',
        'rare',
        'Storm Knot',
        (
            (105, 0, 10),
            (80, 0, mf),
            (7, 0, life << 8),
            *((stat, 0, resistance + (extra if stat == element else 0)) for stat in RESISTS),
        ),
        complete=True,
        affix_records=(
            ('prefix', 281),
            ('prefix', 334),
            ('prefix', 372 if element == 39 else 392),
            ('suffix', 174),
            ('suffix', 286),
            ('suffix', 331),
        ),
    )


def cases():
    for element, label in ((39, 'fire'), (41, 'lightning')):
        item = ring(element)
        examples = [
            ('planner-maxima', item, 'true', 'true'),
            ('lower-rolls', ring(element, perfect=False), 'true', 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), 'unknown', None),
        ]
        for stat, affixes, name in (
            (105, (('suffix', 174),), 'cast-rate'),
            (80, (('prefix', 281), ('suffix', 286)), 'magic-find'),
        ):
            for complete, truth, prefix in ((True, 'false', 'absent'), (False, 'unknown', 'unread')):
                candidate = replace(
                    item,
                    raw_stats=tuple(s for s in item.raw_stats if s[0] != stat),
                    complete=complete,
                    affix_records=tuple(a for a in item.affix_records if a not in affixes) if complete else None,
                )
                examples.append((prefix + '-' + name, candidate, truth, None))
        for name, candidate, truth, preference in examples:
            role_expectations = []
            for role in ROLES:
                expected = {'id': role, 'rule_trace': IsPartialDict(truth=truth)}
                if preference is not None:
                    expected['preferences'] = Contains(
                        *(
                            IsPartialDict(label=text, status=preference)
                            for text in (
                                '40 life',
                                '25% magic find',
                                '41% fire or lightning resistance',
                                '11% all resistances',
                            )
                        )
                    )
                role_expectations.append(IsPartialDict(**expected))
            expected = {'roles': Contains(*role_expectations)}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(*CONFIGS))
                            for key in ('105:0', '80:0', '7:0', '39:0', '41:0', '43:0', '45:0')
                        }
                    )
                )
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=7, raw=(40 if name == 'planner-maxima' else 31) << 8),
                            roll_range=IsPartialDict(min=31, max=40),
                        ),
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=80),
                            roll_range=IsPartialDict(min=10, max=25),
                            roll_quality='perfect' if name == 'planner-maxima' else 'low',
                            roll_tier=1,
                        ),
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=element),
                            roll_range=IsPartialDict(min=29, max=41),
                            roll_quality_range=IsPartialDict(min=8, max=41),
                            roll_quality='perfect' if name == 'planner-maxima' else 'normal',
                            roll_tier=1,
                        ),
                    )
                )
            yield Case(
                id=f'blizzard-rare-rings/{label}/{name}',
                item=candidate,
                context={'player_class': 'Sorceress'},
                covers=ROLES,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected=result,
                absent_configurations=() if truth == 'true' else CONFIGS,
                report_contains=('Ring', 'Faster Cast Rate', 'Blizzard Sorceress') if truth == 'true' else ('Ring',),
                evidence=(
                    'pricing/data/wp-a-builds.json:/blizzard-sorceress/variants/2/player/Rings',
                    'pricing/data/wp-a-builds.json:/blizzard-sorceress/variants/3/player/Rings',
                    'third-parties/d2data/json/magicprefix.json:/281',
                    'third-parties/d2data/json/magicprefix.json:/334',
                    f'third-parties/d2data/json/magicprefix.json:/{372 if element == 39 else 392}',
                    'third-parties/d2data/json/magicsuffix.json:/174',
                    'third-parties/d2data/json/magicsuffix.json:/286',
                    'third-parties/d2data/json/magicsuffix.json:/331',
                ),
            )


CASES = tuple(cases())
