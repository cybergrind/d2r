"""Two equipped Lawbringers require two explicit legal weapon-slot snapshots."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from pricing.knowledge.assessment.adapters.capture import normalize
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'zeal-paladin-dual-lawbringer-starter'


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
        weapon = normalize(item.capture()).to_dict()
        other = normalize(replace(item, base='Cryptic Sword', ethereal=True).capture()).to_dict()
        twohand = normalize(replace(item, base='Legend Sword').capture()).to_dict()
        for label, equipment, scenario in (
            ('two-equipped', {'weapon': weapon, 'off_hand': other}, 'positive'),
            ('one-equipped', {'weapon': weapon, 'off_hand': None}, 'negative'),
            ('other-slot-unknown', {'weapon': weapon}, 'unknown'),
            ('two-handed-other', {'weapon': weapon, 'off_hand': twohand}, 'negative'),
            ('unknown-loadout', None, 'unknown'),
        ):
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=ROLE,
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                        ),
                    )
                )
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))
                            for key in ('151:119', '198:5583')
                        }
                    )
                )
            result.append(
                Case(
                    id=f'zeal/dual-lawbringer/{quality}/{label}',
                    item=item,
                    context={
                        'player_class': 'Paladin',
                        'mercenary_type': 'Act 5 Frenzy',
                        'mercenary_equipment': equipment,
                        'mercenary_items': ['Lawbringer', 'Lawbringer'],
                    },
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(ROLE,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (ROLE + '-stats',),
                    report_contains=('Lawbringer',),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/sections/13',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
