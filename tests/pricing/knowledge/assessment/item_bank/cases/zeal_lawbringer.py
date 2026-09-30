"""Completed mercenary swords retain quality, handedness and bearer distinctions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'zeal-paladin-lawbringer-act-5-frenzy'
CONTEXT = {'player_class': 'Paladin', 'mercenary_type': 'Act 5 Frenzy'}


def make_case(quality, scenario, item, context):
    expected = {
        'roles': Contains(
            IsPartialDict(
                id=ROLE,
                side='merc',
                status='failed' if scenario == 'negative' else 'partial',
                rule_trace=IsPartialDict(
                    truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                ),
            )
        )
    }
    if scenario == 'positive':
        expected['stat_evaluation'] = IsPartialDict(
            annotations=IsPartialDict(
                {key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats')) for key in ('151:119', '198:5583')}
            )
        )
    return Case(
        id='zeal/lawbringer/' + quality + '/' + scenario,
        item=item,
        context=context,
        expected={'assessment': IsPartialDict(**expected)},
        covers=(ROLE,),
        scenario=scenario,
        absent_configurations=() if scenario == 'positive' else (ROLE + '-stats',),
        report_contains=('Lawbringer',),
        evidence=(
            'pricing/raw/mr/guides__zeal-paladin.html:mercenary-gear',
            'third-parties/d2data/json/runes.json:/Lawbringer',
        ),
    )


def cases():
    result = []
    for quality in ('normal', 'superior', 'low_quality'):
        item = Item(
            'Phase Blade',
            quality,
            'Lawbringer',
            ((151, 119, 16), (198, 5583, 20), (60, 0, 7)),
            runeword='Lawbringer',
            sockets=3,
            socket_contents='filled',
        )
        result.extend(
            (
                make_case(quality, 'positive', item, CONTEXT),
                make_case(quality, 'negative', replace(item, base='Legend Sword'), CONTEXT),
                make_case(quality, 'unknown', item, {'player_class': 'Paladin'}),
            )
        )
    ethereal = replace(result[0].item, base='Cryptic Sword', ethereal=True)
    result.append(make_case('ethereal-cryptic', 'positive', ethereal, CONTEXT))
    return tuple(result)


CASES = cases()
