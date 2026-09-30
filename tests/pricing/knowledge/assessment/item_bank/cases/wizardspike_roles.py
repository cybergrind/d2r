"""Native Wizardspike casting utility in reviewed player and swap slots."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SLOTS = (
    ('blizzard-sorceress', 'Sorceress', 'Weapon', 6),
    ('dragon-talon-assassin', 'Assassin', 'Weapon', 4),
    ('dream-paladin', 'Paladin', 'Weapon-Swap', 1),
    ('echoing-strike-warlock-guide', 'Warlock', 'Weapon', 11),
    ('fire-warlock-guide', 'Warlock', 'Weapon', 11),
    ('fist-of-the-heavens-paladin', 'Paladin', 'Weapon', 2),
    ('gold-find-barbarian', 'Barbarian', 'Weapon-Swap', 3),
    ('gold-find-barbarian', 'Barbarian', 'Off-Hand-Swap', 3),
    ('lightning-fury-amazon-guide', 'Amazon', 'Weapon-Swap', 6),
    ('lightning-sentry-assassin', 'Assassin', 'Weapon', 4),
    ('lightning-sorceress', 'Sorceress', 'Weapon', 8),
    ('lightning-sorceress', 'Sorceress', 'Weapon-Swap', 6),
    ('lightning-strike-amazon', 'Amazon', 'Weapon-Swap', 5),
    ('meteor-sorceress', 'Sorceress', 'Weapon', 5),
    ('wake-of-fire-assassin', 'Assassin', 'Weapon', 3),
)
TABLES = (
    ('blood-boil-warlock-guide', 'Warlock', 29),
    ('summoner-warlock-guide', 'Warlock', 29),
    ('fire-wall-sorceress-guide', 'Sorceress', 30),
    ('frozen-orb-meteor-sorceress', 'Sorceress', 29),
    ('frozen-orb-sorceress', 'Sorceress', 29),
    ('hydra-sorceress', 'Sorceress', 29),
    ('summoner-necromancer-guide', 'Necromancer', 33),
)


def uses():
    for guide, player_class, slot, index in SLOTS:
        yield (
            f'{guide}-wizardspike-{slot.lower()}-utility-alternative',
            player_class,
            False,
            (f'pricing/data/wp-a-builds.json:/{guide}/slots/{slot}/{index}'),
        )
    for guide, player_class, section in TABLES:
        suffix = 'summoner-caster-gear' if player_class == 'Necromancer' else 'caster-weapon-gear'
        yield (
            f'{guide}-wizardspike-{suffix}',
            player_class,
            True,
            (
                'pricing/data/appraisal-guide-sections.json:/sources/'
                f'pricing~1raw~1mr~1guides__{guide}.html/sections/{section}'
            ),
        )


def cases():
    item = Item(
        'Bone Knife',
        'unique',
        'Wizardspike',
        raw_stats=(
            (105, 0, 50),
            (39, 0, 75),
            (41, 0, 75),
            (43, 0, 75),
            (45, 0, 75),
            (217, 0, 16 << 8),
            (77, 0, 15),
            (27, 0, 15),
        ),
        viewer_level=80,
    )
    for role, player_class, table, source in uses():
        context = {'player_class': player_class}
        examples = [
            ('native', item, context, 'true'),
            ('open-socket', replace(item, sockets=1), context, 'true'),
            ('unknown-payload', replace(item, sockets=1, socket_contents='unknown'), context, 'true'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Druid'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('impossible-ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
        ]
        if table:
            examples.extend(
                (
                    ('illegal-two-sockets', replace(item, sockets=2), context, 'false'),
                    ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                )
            )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                            for key in ('105:0', '39:0', '41:0', '43:0', '45:0', '217:0', '77:0', '27:0')
                        }
                    )
                )
            yield Case(
                id=f'wizardspike-roles/{role}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=(role,),
                expected={'assessment': IsPartialDict(**expected)},
                report_contains=('Wizardspike', '50% Faster Cast Rate', '+160 to Mana', 'Trade tier:')
                if truth == 'true'
                else ('Bone Knife',),
                evidence=(source, 'third-parties/d2data/json/uniqueitems.json:/262'),
            )


CASES = tuple(cases())
