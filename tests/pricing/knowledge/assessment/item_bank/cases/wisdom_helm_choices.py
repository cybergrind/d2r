"""Wisdom distinguishes projectile utility, physical leech and trap support."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


SPECS = (
    ('double-throw-barbarian-guide', 'Barbarian', 11, ('156:0', '62:0', '119:0')),
    ('enchant-sorceress', 'Sorceress', 4, ('156:0', '62:0', '119:0')),
    ('lightning-fury-amazon-guide', 'Amazon', 5, ('156:0', '62:0')),
    ('wake-of-fire-assassin', 'Assassin', 5, ()),
)
RUNES = tuple(SocketItem(n + ' Rune') for n in ('Pul', 'Ith', 'Eld'))


def helm(quality, maximum=False):
    # Native word plus Pul armor defense, Ith damage-to-mana and Eld stamina.
    # No base/total defense is fabricated; this is an incomplete observation.
    return NativeRunewordItem(
        'Bone Visage',
        quality,
        'Wisdom',
        (
            (153, 0, 1),
            (138, 0, 5),
            (1, 0, 10),
            (156, 0, 33),
            (62, 0, 8 if maximum else 4),
            (119, 0, 25 if maximum else 15),
            (16, 0, 30),
            (114, 0, 15),
            (154, 0, 15),
            (194, 0, 3),
        ),
        sockets=3,
        socket_contents='filled',
        socket_items=RUNES,
        runeword='Wisdom',
    )


def cases():
    for build, klass, index, attack_keys in SPECS:
        role = f'{build}-player-wisdom-helmets-main-alternatives-helm-word-alternative'
        config = role + '-stats'
        context = {'player_class': klass}
        keys = ('153:0', '138:0', '1:0', *attack_keys)
        excluded = tuple(k for k in ('156:0', '62:0', '119:0') if k not in attack_keys)
        for quality in ('normal', 'superior', 'low_quality'):
            item = helm(quality)
            for label, candidate, loadout, truth in (
                ('minimum', item, context, 'true'),
                ('maximum', helm(quality, True), context, 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', observation(item, ethereal=None), context, 'unknown'),
                ('wrong-class', item, {'player_class': 'Druid'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('empty', replace(item, socket_items=(), socket_contents='empty'), context, 'false'),
                ('wrong-recipe', replace(item, socket_items=RUNES[::-1]), context, 'false'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-family', replace(item, base='Mage Plate'), context, 'false'),
            ):
                active = truth == 'true'
                expected = {}
                if label not in ('empty', 'wrong-recipe', 'unidentified', 'wrong-family'):
                    expected['roles'] = Contains(
                        IsPartialDict(
                            id=role,
                            side='player',
                            rule_trace=IsPartialDict(truth=truth),
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
                                            desirability='supporting' if key == '1:0' else 'desirable',
                                        )
                                    )
                                )
                                for key in keys
                            }
                        )
                    )
                yield Case(
                    id=f'wisdom-helm-choices/{build}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(excluded, (config,)),
                    report_contains=('Wisdom', 'Pul, Ith, Eld') if active else (),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/slots/Helmets/{index}',
                        'third-parties/d2data/json/runes.json:/Wisdom',
                        'third-parties/d2data/json/gems.json',
                    ),
                )


CASES = tuple(cases())
