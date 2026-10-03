"""Leaf fire skills are cross-class; its Sorceress skills and weapon fire damage are not."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


SPECS = (
    ('enchant-sorceress', 'Sorceress', 5),
    ('fire-warlock-guide', 'Warlock', 4),
    ('fissure-druid', 'Druid', 7),
)
RUNES = tuple(SocketItem(r + ' Rune') for r in ('Tir', 'Ral'))


def leaf(quality):
    return NativeRunewordItem(
        'Battle Staff',
        quality,
        'Leaf',
        (
            (126, 1, 3),
            (43, 0, 33),
            (138, 0, 2),
            (214, 0, 16),
            (107, 41, 3),
            (107, 36, 3),
            (107, 37, 3),
            (48, 0, 5),
            (49, 0, 30),
            (194, 0, 2),
        ),
        sockets=2,
        socket_contents='filled',
        runeword='Leaf',
        socket_items=RUNES,
    )


def cases():
    for build, klass, index in SPECS:
        role = f'{build}-player-leaf-weapon-main-alternatives-caster-word-remainder'
        config = role + '-stats'
        context = {'player_class': klass}
        priorities = {'126:1': 'desirable', '43:0': 'supporting', '138:0': 'desirable', '214:0': 'supporting'}
        if klass == 'Sorceress':
            priorities['107:37'] = 'desirable'
        for quality in ('normal', 'superior', 'low_quality'):
            item = leaf(quality)
            for label, candidate, loadout, truth in (
                ('native', item, context, 'true'),
                ('ethereal-casting', replace(item, ethereal=True), context, 'true'),
                ('unknown-ethereal', observation(item, ethereal=None), context, 'true'),
                ('wrong-class', item, {'player_class': 'Amazon'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-recipe', replace(item, socket_items=RUNES[::-1]), context, 'false'),
                ('empty', replace(item, socket_items=(), socket_contents='empty'), context, 'false'),
                ('polearm', replace(item, base='Thresher'), context, 'false'),
                (
                    'unread-fire-skills',
                    replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 126)),
                    context,
                    'true',
                ),
            ):
                active = truth == 'true'
                expected = {}
                if label not in ('unidentified', 'wrong-recipe', 'empty', 'polearm'):
                    expected['roles'] = Contains(
                        IsPartialDict(
                            id=role,
                            side='player',
                            rule_trace=IsPartialDict(truth=truth),
                            missing=Contains(
                                'Fire skill levels benefit eligible fire skills, not every class skill. '
                                'Sorceress Warmth soft levels do not count as Enchant hard-point synergy; '
                                'native staffmods are assessed separately. Inserted fire damage is weapon damage, '
                                'not a spell multiplier.'
                            ),
                        )
                    )
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(
                                    contributions=Contains(
                                        IsPartialDict(
                                            configuration_id=config,
                                            desirability=priority,
                                        )
                                    )
                                )
                                for key, priority in priorities.items()
                                if label != 'unread-fire-skills' or key != '126:1'
                            }
                        )
                    )
                ignored = ('48:0', '49:0', '107:36', '107:41', '105:0')
                if klass != 'Sorceress':
                    ignored += ('107:37',)
                if label == 'unread-fire-skills':
                    ignored += ('126:1',)
                yield Case(
                    id=f'leaf-fire-choices/{build}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(ignored, (config,)),
                    report_contains=('Leaf', 'Tir, Ral') if active else (),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/slots/Weapon/{index}',
                        'third-parties/d2data/json/runes.json:/Leaf',
                        'third-parties/d2data/json/gems.json',
                    ),
                )


CASES = tuple(cases())
