"""Shared repairable Fade armor differs from Zeal's ethereal endgame mercenary example."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.cases.treachery_endgame_mercs import armor
from tests.pricing.knowledge.assessment.item_bank.models import Case


USES = (
    (
        'smite-shared-treachery',
        'Mage Plate',
        False,
        ('201:17103', '93:0', '99:0', '43:0'),
        'pricing/data/wp-a-variants/smite-paladin.json:/variants/1/merc/Body Armor',
    ),
    (
        'zeal-paladin-treachery-fade-prebuff',
        'Mage Plate',
        False,
        ('201:17103',),
        'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/sections/32',
    ),
    (
        'zeal-paladin-merc-word-treachery-end',
        'Archon Plate',
        True,
        ('93:0', '99:0', '43:0', '201:17103', '198:17807', '79:0'),
        'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/item_spans/226',
    ),
)


def cases():
    for role, base, ethereal, keys, source in USES:
        config = role + '-stats'
        context = {'player_class': 'Paladin', 'mercenary_type': 'Act 2 Might'}
        prebuff = role == 'zeal-paladin-treachery-fade-prebuff'
        shared = role == 'smite-shared-treachery'
        for quality in ('normal', 'superior', 'low_quality'):
            item = replace(armor(base, quality), ethereal=ethereal)
            examples = (
                ('native', item, context, 'true', True),
                ('opposite-ethereal', replace(item, ethereal=not ethereal), context, 'false', False),
                ('unknown-ethereal', observation(item, ethereal=None), context, 'unknown', False),
                ('wrong-class', item, dict(context, player_class='Sorceress'), 'false', False),
                ('unknown-class', item, {'mercenary_type': 'Act 2 Might'}, 'unknown', False),
                (
                    'wrong-merc',
                    item,
                    dict(context, mercenary_type='Act 5 Frenzy'),
                    'true' if shared or prebuff else 'false',
                    prebuff,
                ),
                (
                    'unknown-merc',
                    item,
                    {'player_class': 'Paladin'},
                    'true' if shared or prebuff else 'unknown',
                    prebuff,
                ),
                ('wrong-recipe', replace(item, socket_items=item.socket_items[::-1]), context, 'false', False),
                ('empty', replace(item, socket_items=(), socket_contents='empty'), context, 'false', False),
                ('unidentified', replace(item, identified=False), context, 'false', False),
            )
            for label, candidate, loadout, truth, active in examples:
                bad_identity = label in ('wrong-recipe', 'empty', 'unidentified')
                assessment = (
                    {}
                    if bad_identity
                    else {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                )
                if active:
                    assessment['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in keys}
                        )
                    )
                expected = {'assessment': IsPartialDict(**assessment)}
                if bad_identity:
                    expected['extraction'] = IsPartialDict(item=IsPartialDict(runeword=None))
                excluded = {'83:6': (config,)}
                if prebuff:
                    excluded.update(dict.fromkeys(('93:0', '99:0', '43:0', '79:0', '198:17807'), (config,)))
                yield Case(
                    id=f'treachery-shared/{role}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=(role,),
                    scenario='positive' if active else 'unknown' if label.startswith('unknown-') else 'negative',
                    expected=expected,
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=excluded,
                    report_contains=('Treachery', 'Sockets: 3 — Shael, Thul, Lem', 'Fade') if label == 'native' else (),
                    evidence=(
                        source,
                        'third-parties/d2data/json/runes.json:/Treachery',
                        'pricing/raw/mr/planners/fc01065b.json:/data',  # Decoded items/54 in this JSON string.,
                    )
                    if ethereal
                    else (source, 'third-parties/d2data/json/runes.json:/Treachery'),
                )


CASES = tuple(cases())
