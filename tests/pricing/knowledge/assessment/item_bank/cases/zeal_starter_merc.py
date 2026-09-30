"""Zeal starter Act 5 branches: bearer stats and explicit handedness."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def case(role, label, item, mercenary, keys, scenario='positive', absent=()):
    context = {'player_class': 'Paladin'}
    if mercenary:
        context['mercenary_type'] = mercenary
    expected = {
        'roles': Contains(
            IsPartialDict(
                id=role,
                side='merc',
                rule_trace=IsPartialDict(
                    truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                ),
            )
        ),
    }
    if scenario == 'positive':
        expected['stat_evaluation'] = IsPartialDict(
            annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys})
        )
    return Case(
        id='zeal/starter-merc/' + role + '/' + label,
        item=item,
        context=context,
        expected={'assessment': IsPartialDict(**expected)},
        covers=(role,),
        scenario=scenario,
        absent_configurations=() if scenario == 'positive' else (role + '-stats',),
        absent_stat_configurations=dict.fromkeys(absent, (role + '-stats',)),
        report_contains=(item.name,),
        evidence=(
            'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/sections/13',
        ),
    )


def cases():
    result = []
    for branch in ('frenzy', 'bash'):
        merc = 'Act 5 ' + branch.title()
        role = 'zeal-paladin-smoke-act-5-' + branch
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                'Mage Plate',
                quality,
                'Smoke',
                ((39, 0, 50), (41, 0, 50), (43, 0, 50), (45, 0, 50), (99, 0, 20), (1, 0, 10), (32, 0, 280)),
                runeword='Smoke',
                sockets=2,
                socket_contents='filled',
                ethereal=True,
            )
            keys = ('39:0', '41:0', '43:0', '45:0', '99:0', '32:0')
            result.extend(
                (
                    case(role, quality + '/resistance', item, merc, keys, absent=('1:0',)),
                    case(role, quality + '/empty', replace(item, socket_contents='empty'), merc, keys, 'negative'),
                    case(role, quality + '/unknown-merc', item, None, keys, 'unknown'),
                )
            )
        role = 'zeal-paladin-crown-of-thieves-act-5-' + branch
        item = Item(
            'Grand Crown',
            'unique',
            'Crown of Thieves',
            ((60, 0, 9), (39, 0, 33), (7, 0, 50 * 256), (9, 0, 35 * 256), (79, 0, 80), (2, 0, 25), (16, 0, 160)),
            ethereal=True,
        )
        keys = ('60:0', '39:0', '7:0', '79:0', '2:0', '16:0')
        result.extend(
            (
                case(role, 'ethereal-low-leech', item, merc, keys, absent=('9:0',)),
                case(
                    role,
                    'upgraded-nonethereal',
                    replace(item, base='Corona', ethereal=False),
                    merc,
                    keys,
                    absent=('9:0',),
                ),
                case(role, 'wrong-merc', item, 'Act 2 Might', keys, 'negative'),
                case(role, 'unknown-merc', item, None, keys, 'unknown'),
                case(
                    role,
                    'missing-leech',
                    replace(item, raw_stats=((39, 0, 33),)),
                    merc,
                    ('39:0',),
                    absent=('60:0', '9:0'),
                ),
            )
        )
    role = 'zeal-paladin-lawbringer-act-5-bash'
    for quality in ('normal', 'superior', 'low_quality'):
        item = Item(
            'Legend Sword',
            quality,
            'Lawbringer',
            ((151, 119, 16), (198, 5583, 20), (60, 0, 7)),
            runeword='Lawbringer',
            sockets=3,
            socket_contents='filled',
            ethereal=True,
        )
        keys = ('151:119', '198:5583', '60:0')
        result.extend(
            (
                case(role, quality + '/two-handed', item, 'Act 5 Bash', keys),
                case(
                    role,
                    quality + '/one-handed',
                    replace(item, base='Phase Blade', ethereal=False),
                    'Act 5 Bash',
                    keys,
                    'negative',
                ),
                case(role, quality + '/unknown-merc', item, None, keys, 'unknown'),
            )
        )
    role = 'zeal-paladin-crown-of-thieves-act-2-might'
    merc = 'Act 2 Might'
    item = Item(
        'Grand Crown',
        'unique',
        'Crown of Thieves',
        ((60, 0, 9), (39, 0, 33), (7, 0, 50 * 256), (9, 0, 35 * 256), (79, 0, 80), (2, 0, 25), (16, 0, 160)),
        ethereal=True,
    )
    keys = ('60:0', '39:0', '7:0', '79:0', '2:0', '16:0')
    result.extend(
        (
            case(role, 'ethereal-low-leech', item, merc, keys, absent=('9:0',)),
            case(
                role, 'upgraded-nonethereal', replace(item, base='Corona', ethereal=False), merc, keys, absent=('9:0',)
            ),
            case(role, 'wrong-merc', item, 'Act 5 Frenzy', keys, 'negative'),
            case(role, 'unknown-merc', item, None, keys, 'unknown'),
            case(
                role, 'missing-leech', replace(item, raw_stats=((39, 0, 33),)), merc, ('39:0',), absent=('60:0', '9:0')
            ),
        )
    )
    return tuple(result)


CASES = cases()
