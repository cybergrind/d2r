"""Native Suicide Branch caster contributions, including upgraded and ethereal wands."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    ('abyss-warlock-build-guide', 'Warlock', 9),
    ('blessed-hammer-paladin', 'Paladin', 4),
    ('echoing-strike-warlock-guide', 'Warlock', 18),
    ('fire-blast-assassin', 'Assassin', 2),
    ('fire-warlock-guide', 'Warlock', 9),
    ('fist-of-the-heavens-paladin', 'Paladin', 3),
    ('lightning-sentry-assassin', 'Assassin', 6),
    ('wake-of-fire-assassin', 'Assassin', 5),
)
STATS = (
    (78, 0, 25),
    (105, 0, 50),
    (77, 0, 10),
    (7, 0, 40 << 8),
    (127, 0, 1),
    *((stat, 0, 10) for stat in (39, 41, 43, 45)),
)


def cases():
    for guide, player_class, index in (
        *USES,
        ('blood-boil-warlock-guide', 'Warlock', None),
        ('summoner-warlock-guide', 'Warlock', None),
    ):
        role = guide + (
            '-suicide-branch-caster-progression-alternative'
            if index is not None
            else '-suicide-branch-caster-weapon-gear'
        )
        evidence = (
            f'pricing/data/wp-a-builds.json:/{guide}/slots/Weapon/{index}'
            if index is not None
            else (
                'pricing/data/appraisal-guide-sections.json:/sources/'
                f'pricing~1raw~1mr~1guides__{guide}.html/sections/29'
            )
        )
        config = role + '-stats'
        context = {'player_class': player_class}
        item = Item('Burnt Wand', 'unique', 'Suicide Branch', STATS, complete=True)
        for label, candidate, loadout, truth in (
            ('native', item, context, 'true'),
            ('upgraded', replace(item, base='Polished Wand'), context, 'true'),
            ('ethereal-casting', replace(item, ethereal=True), context, 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Druid'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        ):
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(config))
                            for key in ('127:0', '105:0', '77:0', '7:0', '39:0', '41:0', '43:0', '45:0')
                        }
                    )
                )
            yield Case(
                id=f'suicide-branch/{guide}/{label}',
                item=candidate,
                context=loadout,
                scenario='unknown'
                if label.startswith('unknown')
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=(role,),
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if truth == 'true' else (config,),
                absent_stat_configurations={'78:0': (config,)},
                report_contains=('Trade tier:', '50% Faster Cast Rate') if truth == 'true' else (),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/139',
                    evidence,
                ),
            )


CASES = tuple(cases())
