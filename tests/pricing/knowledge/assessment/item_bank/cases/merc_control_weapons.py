"""Native Lawbringer control and Obedience damage alternatives, with bearer boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('double-throw-barbarian-guide', 'Barbarian', 'Act 5 Frenzy', 'early', 'Lawbringer', 2),
    ('fissure-druid', 'Druid', 'Act 5 Bash', 'early', 'Lawbringer', 1),
    ('fissure-druid', 'Druid', 'Act 5 Frenzy', 'early', 'Lawbringer', 1),
    ('fissure-druid', 'Druid', 'Act 5 Bash', 'mid', 'Lawbringer', 1),
    ('fissure-druid', 'Druid', 'Act 5 Frenzy', 'mid', 'Lawbringer', 1),
    ('strafe-amazon', 'Amazon', 'Act 2 Might', 'mid', 'Obedience', 1),
)


def weapon(name, merc, quality, maximum=False):
    if name == 'Lawbringer':
        base = 'Cryptic Sword' if merc == 'Act 5 Frenzy' else 'Legend Sword'
        stats = (
            (151, 119, 18 if maximum else 16),
            (198, 5583, 20),
            (60, 0, 7),
            (32, 0, 250 if maximum else 200),
            (2, 0, 10),
            (116, 0, 50),
            (48, 0, 150),
            (49, 0, 210),
            (54, 0, 130),
            (55, 0, 180),
        )
        sockets = 3
    else:
        base = 'Thresher'
        resist = 30 if maximum else 20
        stats = (
            (17, 0, 370),
            (18, 0, 370),
            (136, 0, 40),
            (39, 0, resist),
            (41, 0, resist),
            (43, 0, resist + 30),
            (45, 0, resist),
            (31, 0, 300 if maximum else 200),
            (99, 0, 40),
            (196, 3349, 30),
        )
        sockets = 5
    # Deliberately partial captures: no invented total weapon damage or market eligibility.
    return Item(base, quality, name, stats, sockets=sockets, socket_contents='filled', runeword=name)


def cases():
    for build, klass, merc, stage, name, index in SPECS:
        role = (
            f'{build}-lawbringer-{stage}-{merc.lower().replace(" ", "-")}-merc-sword-tail'
            if name == 'Lawbringer'
            else f'{build}-obedience-{stage}-merc-weapon-alternative'
        )
        config = role + '-stats'
        context = {'player_class': klass, 'mercenary_type': merc}
        desirable = (
            ('151:119', '198:5583')
            if name == 'Lawbringer'
            else (
                '17:0',
                '18:0',
                '136:0',
                '39:0',
                '41:0',
                '43:0',
                '45:0',
            )
        )
        for quality in ('normal', 'superior', 'low_quality'):
            item = weapon(name, merc, quality)
            scenarios = [
                ('minimum', item, context, 'true'),
                ('maximum', weapon(name, merc, quality, True), context, 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
                ('empty', replace(item, socket_contents='empty'), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
                ('wrong-count', replace(item, sockets=2), context, 'false'),
                ('unknown-count', replace(item, sockets=None), context, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {**context, 'player_class': 'Warlock'}, 'false'),
                ('unknown-class', item, {'mercenary_type': merc}, 'unknown'),
                ('wrong-merc', item, {**context, 'mercenary_type': 'Act 1 Fire'}, 'false'),
                ('unknown-merc', item, {'player_class': klass}, 'unknown'),
                (
                    'wrong-family',
                    replace(item, base='Crystal Sword' if name == 'Obedience' else 'Thresher'),
                    context,
                    'false',
                ),
            ]
            if merc == 'Act 5 Frenzy':
                scenarios.append(('two-handed', replace(item, base='Legend Sword'), context, 'false'))
            for label, candidate, loadout, truth in scenarios:
                active = truth == 'true'
                expected = {}
                if label != 'wrong-family':
                    expected['roles'] = Contains(
                        IsPartialDict(
                            id=role,
                            side='merc',
                            rule_trace=IsPartialDict(truth=truth),
                            missing=Contains(
                                'Sanctuary supplies undead control; its physical-immunity bypass belongs to the '
                                'wielder, not the player. Life leech uses the mercenary physical damage, not added '
                                'elemental damage. This weapon has no native ED or IAS; check the rest of the '
                                'mercenary setup.'
                                if name == 'Lawbringer'
                                else 'Enhanced Damage and Crushing Blow affect the mercenary. Enchant requires a '
                                'kill-triggered proc and buffs the wielder, not the player. Enemy fire resistance '
                                'reduction is local to mercenary damage. The weapon supplies no life leech or IAS; '
                                'check both elsewhere in the loadout.'
                            ),
                        )
                    )
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                f'{stat}:{layer}': IsPartialDict(
                                    contributions=Contains(
                                        IsPartialDict(
                                            configuration_id=config,
                                            desirability='desirable'
                                            if f'{stat}:{layer}' in desirable
                                            else 'supporting',
                                        )
                                    )
                                )
                                for stat, layer, _ in item.raw_stats
                            }
                        )
                    )
                yield Case(
                    id=f'merc-control-weapons/{build}/{stage}/{merc}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(
                        ('17:0', '18:0', '93:0') if name == 'Lawbringer' else ('60:0', '93:0'),
                        (config,),
                    ),
                    report_contains=(name,),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/merc/Weapon/{stage}/{index}',
                        f'third-parties/d2data/json/runes.json:/{name}',
                    ),
                )


CASES = tuple(cases())
