"""Silkweave wearer mana recovery is not mana leech or summon kill credit."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    ('echoing-strike-warlock-guide', 'Warlock', 'caster-progression-alternative', 4, None, True),
    ('fire-warlock-guide', 'Warlock', 'caster-progression-alternative', 5, None, True),
    ('fist-of-the-heavens-paladin', 'Paladin', 'caster-progression-alternative', 4, None, True),
    ('lightning-fury-amazon-guide', 'Amazon', 'caster-progression-alternative', 2, None, True),
    ('lightning-sorceress', 'Sorceress', 'caster-progression-alternative', 3, None, True),
    ('nova-sorceress-guide', 'Sorceress', 'caster-progression-alternative', 0, None, True),
    ('blood-boil-warlock-guide', 'Warlock', 'caster-accessory-gear', None, 29, True),
    ('summoner-warlock-guide', 'Warlock', 'caster-accessory-gear', None, 29, False),
    ('summoner-necromancer-guide', 'Necromancer', 'summoner-caster-gear', None, 33, True),
)


def cases():
    item = Item(
        'Mesh Boots',
        'unique',
        'Silkweave',
        raw_stats=((96, 0, 30), (77, 0, 10), (138, 0, 5), (32, 0, 200), (16, 0, 170)),
    )
    for guide, player_class, suffix, index, section, wearer_recovery in USES:
        role = f'{guide}-silkweave-{suffix}'
        source = (
            f'pricing/data/wp-a-builds.json:/{guide}/slots/Boots/{index}'
            if section is None
            else (
                'pricing/data/appraisal-guide-sections.json:/sources/'
                f'pricing~1raw~1mr~1guides__{guide}.html/sections/{section}'
            )
        )
        context = {'player_class': player_class}
        for label, candidate, loadout, truth, scenario in (
            ('native', item, context, 'true', 'positive'),
            ('upgraded', replace(item, base='Boneweave Boots'), context, 'true', 'positive'),
            ('unidentified', replace(item, identified=False), context, 'false', 'negative'),
            ('ethereal', replace(item, ethereal=True), context, 'false', 'negative'),
            ('unread-ethereal', replace(item, ethereal=None), context, 'unknown', 'unknown'),
            ('wrong-class', item, {'player_class': 'Barbarian'}, 'false', 'negative'),
            ('unread-class', item, {}, 'unknown', 'unknown'),
            ('invalid-sockets', replace(item, sockets=1), context, 'false', 'negative'),
            ('unread-sockets', replace(item, sockets=None), context, 'unknown', 'unknown'),
        ):
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if scenario == 'positive':
                keys = ('96:0', '77:0', '32:0') + (('138:0',) if wearer_recovery else ())
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'silkweave-alternative/{guide}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=(role,),
                expected={'assessment': IsPartialDict(**expected)},
                absent_stat_configurations={} if wearer_recovery else {'138:0': (role + '-stats',)},
                report_contains=('Silkweave',),
                evidence=(source, 'third-parties/d2data/json/uniqueitems.json:/239'),
            )


CASES = tuple(cases())
