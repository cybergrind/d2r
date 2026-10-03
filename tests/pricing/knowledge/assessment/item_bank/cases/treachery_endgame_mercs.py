"""Mercenary Treachery components preserve source-specific ethereal and proc roles."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


USES = (
    ('enchant-sorceress', 0, 'Sorceress', 'Act 1 Fire', 'Mage Plate', True),
    ('gold-find-barbarian', 0, 'Barbarian', 'Act 2 Might', 'Mage Plate', False),
    ('dream-paladin', 0, 'Paladin', 'Act 2 Might', 'Archon Plate', True),
    ('lightning-fury-amazon-guide', 3, 'Amazon', 'Act 5 Frenzy', 'Mage Plate', True),
    ('lightning-sorceress', 3, 'Sorceress', 'Act 5 Frenzy', 'Archon Plate', False),
    ('lightning-strike-amazon', 2, 'Amazon', 'Act 5 Frenzy', 'Archon Plate', True),
    ('meteor-sorceress', 4, 'Sorceress', 'Act 2 Might', 'Archon Plate', False),
    ('fire-warlock-guide', 0, 'Warlock', 'Act 2 Might', 'Mage Plate', True),
    ('nova-sorceress-guide', 0, 'Sorceress', 'Act 2 Holy Freeze', 'Light Plate', True),
    ('strafe-amazon', 0, 'Amazon', 'Act 2 Might', 'Mage Plate', True),
    ('summoner-necromancer-guide', 0, 'Necromancer', 'Act 2 Might', 'Breast Plate', True),
)
RUNES = tuple(SocketItem(n + ' Rune') for n in ('Shael', 'Thul', 'Lem'))


def armor(base, quality):
    return NativeRunewordItem(
        base,
        quality,
        'Treachery',
        (
            (194, 0, 3),
            (83, 6, 2),
            (93, 0, 45),
            (99, 0, 20),
            (43, 0, 30),
            (79, 0, 50),
            (201, 267 * 64 + 15, 5),
            (198, 278 * 64 + 15, 25),
        ),
        ethereal=True,
        sockets=3,
        socket_contents='filled',
        socket_items=RUNES,
        runeword='Treachery',
        complete=True,
    )


def cases():
    for guide, variant, klass, merc, base, requires_eth in USES:
        role = f'{guide}-{variant}-merc-treachery-native'
        config = role + '-stats'
        context = {'player_class': klass, 'mercenary_type': merc, 'activity': 'Uber Mephisto'}
        for quality in ('normal', 'superior', 'low_quality'):
            item = armor(base, quality)
            examples = [
                ('native', item, context, 'true'),
                ('nonethereal', replace(item, ethereal=False), context, 'false' if requires_eth else 'true'),
                ('unknown-ethereal', observation(item, ethereal=None), context, 'unknown'),
                ('wrong-class', item, dict(context, player_class='Assassin'), 'false'),
                (
                    'wrong-merc',
                    item,
                    dict(context, mercenary_type='Act 2 Might' if merc == 'Act 1 Fire' else 'Act 1 Fire'),
                    'false',
                ),
                ('unknown-merc', item, {k: v for k, v in context.items() if k != 'mercenary_type'}, 'unknown'),
                ('wrong-recipe', replace(item, socket_items=RUNES[::-1]), context, 'false'),
                ('empty', replace(item, socket_items=(), socket_contents='empty'), context, 'false'),
                ('unidentified', replace(item, identified=False), context, 'false'),
            ]
            if guide == 'lightning-sorceress':
                examples.extend(
                    (
                        ('wrong-activity', item, dict(context, activity='Cows'), 'false'),
                        ('unknown-activity', item, {k: v for k, v in context.items() if k != 'activity'}, 'unknown'),
                    )
                )
            for label, candidate, loadout, truth in examples:
                bad_identity = label in ('wrong-recipe', 'empty', 'unidentified')
                assessment = (
                    {}
                    if bad_identity
                    else {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                )
                keys = ['201:17103', '99:0', '43:0']
                if merc != 'Act 5 Frenzy':
                    keys.append('93:0')
                if guide == 'gold-find-barbarian':
                    keys.append('79:0')
                if truth == 'true':
                    assessment['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(
                                    contributions=Contains(
                                        IsPartialDict(
                                            configuration_id=config,
                                            desirability='supporting' if key in ('99:0', '43:0') else 'desirable',
                                        )
                                    )
                                )
                                for key in keys
                            }
                        )
                    )
                expected = {'assessment': IsPartialDict(**assessment)}
                if bad_identity:
                    expected['extraction'] = IsPartialDict(item=IsPartialDict(runeword=None))
                excluded = {'83:6': (config,), '198:17807': (config,), '79:0': (config,)}
                if guide == 'gold-find-barbarian':
                    del excluded['79:0']
                if merc == 'Act 5 Frenzy':
                    excluded['93:0'] = (config,)
                yield Case(
                    id=f'treachery-endgame/{guide}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected=expected,
                    absent_configurations=() if truth == 'true' else (config,),
                    absent_stat_configurations=excluded,
                    report_contains=(
                        'Treachery',
                        'Sockets: 3 — Shael, Thul, Lem',
                        '5% Chance to cast level 15 Fade when struck',
                        '45% Increased Attack Speed',
                        '20% Faster Hit Recovery',
                        'Cold Resist +30%',
                    )
                    if label == 'native'
                    else (),
                    evidence=(
                        'third-parties/d2data/json/runes.json:/Treachery',
                        f'pricing/data/wp-a-builds.json:/{guide}/variants/{variant}',
                    ),
                )


CASES = tuple(cases())
