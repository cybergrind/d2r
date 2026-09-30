"""Nightwing/Vipermagi alternative: wearer helmet evidence and total casting rate."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from pricing.knowledge.assessment.adapters.capture import normalize
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'blizzard-sorceress-1-vipermagi'


def cases():
    helm = Item('Spired Helm', 'unique', "Nightwing's Veil")
    head = normalize(helm.capture()).to_dict()
    full = {'player_class': 'Sorceress', 'player_total_fcr': 105, 'player_equipment': {'head': head}}
    item = Item(
        'Serpentskin Armor',
        'unique',
        'Skin of the Vipermagi',
        ((105, 0, 30), (127, 0, 1), (35, 0, 9), *((s, 0, 20) for s in (39, 41, 43, 45))),
    )
    rows = [
        ('minimum-resists', item, full, 'true'),
        (
            'maximum-resists',
            replace(item, raw_stats=tuple((s, p, 35 if s in (39, 41, 43, 45) else v) for s, p, v in item.raw_stats)),
            full,
            'true',
        ),
        ('upgraded', replace(item, base='Wyrmhide'), full, 'true'),
        ('empty-socket', replace(item, sockets=1), full, 'true'),
        ('fcr-short', item, {**full, 'player_total_fcr': 104}, 'false'),
        ('fcr-unknown', item, {k: v for k, v in full.items() if k != 'player_total_fcr'}, 'unknown'),
        ('head-empty', item, {**full, 'player_equipment': {'head': None}}, 'false'),
        ('head-unknown', item, {k: v for k, v in full.items() if k != 'player_equipment'}, 'unknown'),
        (
            'wrong-head',
            item,
            {
                **full,
                'player_equipment': {'head': normalize(Item('Shako', 'unique', 'Harlequin Crest').capture()).to_dict()},
            },
            'false',
        ),
        ('ethereal', replace(item, ethereal=True), full, 'false'),
        ('ethereal-unknown', replace(item, ethereal=None), full, 'unknown'),
        ('unidentified', replace(item, identified=False), full, 'false'),
        ('wrong-class', item, {**full, 'player_class': 'Paladin'}, 'false'),
    ]
    for label, candidate, context, truth in rows:
        config = ROLE + '-stats'
        expected = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if truth == 'true':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(config))
                        for key in ('105:0', '127:0', '39:0', '41:0', '43:0', '45:0')
                    }
                )
            )
        yield Case(
            id=f'blizzard/vipermagi/{label}',
            item=candidate,
            context=context,
            expected={'assessment': IsPartialDict(**expected)},
            covers=(ROLE,),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            absent_configurations=() if truth == 'true' else (config,),
            report_contains=('Skin of the Vipermagi',),
            evidence=(
                'pricing/data/wp-a-builds.json:/blizzard-sorceress/variants/1',
                'third-parties/d2data/json/uniqueitems.json',
            ),
        )


CASES = tuple(cases())
