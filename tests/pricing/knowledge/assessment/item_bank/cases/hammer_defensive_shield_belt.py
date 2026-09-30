"""Hammerdin Herald and Thundergod alternatives preserve attack/spell distinctions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.zeal_named_remainder import WORDS
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


HERALD_RAW = next(raw for name, _, _, raw, _ in WORDS if name == 'Herald of Zakarum')
SPECS = (
    (
        'herald-of-zakarum-caster-shield-alternative',
        Item('Gilded Shield', 'unique', 'Herald of Zakarum', HERALD_RAW),
        'Zakarum Shield',
        ('83:3', '188:24', '102:0', '20:0', '0:0', '3:0', '39:0'),
        ('119:0',),
    ),
    (
        'thundergod-s-vigor-defensive-alternative',
        Item(
            'War Belt',
            'unique',
            "Thundergod's Vigor",
            (
                (42, 0, 10),
                (145, 0, 20),
                (0, 0, 20),
                (3, 0, 20),
                (16, 0, 160),
                (97, 34, 3),
                (97, 35, 3),
                (50, 0, 1),
                (51, 0, 50),
                (201, 121 * 64 + 7, 5),
            ),
        ),
        'Colossus Girdle',
        ('42:0', '145:0', '0:0', '3:0'),
        ('97:34', '97:35', '50:0', '51:0', '201:7751'),
    ),
)


def cases():
    context = {'player_class': 'Paladin'}
    for slug, item, upgrade, keys, excluded in SPECS:
        role = 'blessed-hammer-paladin-' + slug
        config = role + '-stats'
        shield = item.base == 'Gilded Shield'
        rows = [
            ('minimum', item, context, 'true'),
            (
                'maximum-defense',
                replace(item, raw_stats=tuple((s, p, 200 if s == 16 else v) for s, p, v in item.raw_stats)),
                context,
                'true',
            ),
            ('upgraded', replace(item, base=upgrade), context, 'true'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('invalid-sockets', replace(item, sockets=2 if shield else 1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        ]
        if shield:
            rows.append(('empty-socket', replace(item, sockets=1), context, 'true'))
        for label, candidate, loadout, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'hammer/defensive-shield-belt/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (config,),
                absent_stat_configurations=dict.fromkeys(excluded, (config,)),
                report_contains=(item.name, 'Trade tier:') if truth == 'true' else (candidate.base,),
                evidence=(
                    'pricing/data/wp-a-builds.json:/blessed-hammer-paladin/slots',
                    'third-parties/d2data/json/uniqueitems.json',
                ),
            )


CASES = tuple(cases())
