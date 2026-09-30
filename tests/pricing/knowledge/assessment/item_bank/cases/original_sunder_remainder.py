"""Remaining explicit original-Sunder uses; native effect and wearer penalty stay distinct."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Independently checked guide charm slots/prose and native uniqueitems401-406.
SPECS = (
    ('blizzard-sorceress', 'Sorceress', 'Cold Rupture', 187, 43, -90, -70),
    ('fire-warlock-guide', 'Warlock', 'Flame Rift', 189, 39, -90, -70),
    ('fissure-druid', 'Druid', 'Flame Rift', 189, 39, -90, -70),
    ('meteor-sorceress', 'Sorceress', 'Flame Rift', 189, 39, -90, -70),
    ('wake-of-fire-assassin', 'Assassin', 'Flame Rift', 189, 39, -90, -70),
    ('lightning-sentry-assassin', 'Assassin', 'Crack of the Heavens', 190, 41, -90, -70),
    ('strafe-amazon', 'Amazon', 'Bone Break', 192, 36, -20, -10),
    ('abyss-warlock-build-guide', 'Warlock', 'Black Cleft', 193, 37, -65, -45),
)


def cases():
    for build, klass, name, effect, penalty, worst, best in SPECS:
        role = build + '-' + name.lower().replace(' ', '-') + '-original-sunder-alternative'
        item = Item('Grand Charm', 'unique', name, ((effect, 0, 300), (penalty, 0, worst)))
        context = {'player_class': klass}
        rows = (
            ('worst-penalty', item, context, 'positive'),
            ('best-penalty', replace(item, raw_stats=((effect, 0, 300), (penalty, 0, best))), context, 'positive'),
            ('wrong-class', item, {'player_class': 'Paladin'}, 'negative'),
            ('unknown-class', item, {}, 'unknown'),
            ('unread-effect', replace(item, raw_stats=((penalty, 0, worst),)), context, 'unknown'),
            (
                'below-native-effect',
                replace(item, raw_stats=((effect, 0, 299), (penalty, 0, worst))),
                context,
                'negative',
            ),
            (
                'above-native-effect',
                replace(item, raw_stats=((effect, 0, 301), (penalty, 0, worst))),
                context,
                'negative',
            ),
            ('unidentified', replace(item, identified=False), context, 'negative'),
            ('socketed', replace(item, sockets=1), context, 'negative'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('crafted-quality', replace(item, rarity='crafted'), context, 'negative'),
        )
        for label, candidate, loadout, scenario in rows:
            expected = {'price_estimate': IsPartialDict(estimate_ist=None)}
            if scenario == 'positive':
                expected['assessment'] = IsPartialDict(
                    roles=Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth='true'))),
                    stat_evaluation=IsPartialDict(
                        annotations=IsPartialDict(
                            {f'{effect}:0': IsPartialDict(configuration_ids=Contains(role + '-stats'))}
                        )
                    ),
                )
                expected['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat={'id': penalty, 'layer': 0, 'raw': worst if label == 'worst-penalty' else best},
                        )
                    )
                )
            yield Case(
                id=f'original-sunder-remainder/{build}/{name}/{label}',
                item=candidate,
                context=loadout,
                expected=expected,
                covers=(f'role:{role}:unique',),
                scenario=scenario,
                absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                report_contains=(name, 'Trade tier:') if scenario == 'positive' else (),
                evidence=(
                    'pricing/data/wp-a-builds.json',
                    'third-parties/d2data/json/uniqueitems.json',
                    'third-parties/d2data/json/itemstatcost.json',
                ),
            )


CASES = tuple(cases())
