"""Magefist casting utility; fire skills help fire spells and Corpse Explosion radius."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'warlock': ('Warlock', False, (('blood-boil-warlock-guide', 29), ('summoner-warlock-guide', 29))),
    'fire': (
        'Sorceress',
        True,
        (('fire-wall-sorceress-guide', 30), ('frozen-orb-meteor-sorceress', 29), ('hydra-sorceress', 29)),
    ),
    'cold': ('Sorceress', False, (('frozen-orb-sorceress', 29),)),
    'corpse-explosion': ('Necromancer', True, (('summoner-necromancer-guide', 33),)),
}
BASES = (('Light Gauntlets', 12), ('Battle Gauntlets', 47), ('Crusader Gauntlets', 68))


def gloves(base, defense, ed=20):
    return Item(
        base,
        'unique',
        'Magefist',
        (
            (105, 0, 20),
            (27, 0, 25),
            (126, 1, 1),
            (48, 0, 1),
            (49, 0, 6),
            (16, 0, ed),
            (31, 0, defense * (100 + ed) // 100 + 10),
        ),
        complete=True,
    )


def cases():
    for group, (player_class, fire, uses) in USES.items():
        suffix = (
            '-magefist-summoner-caster-gear' if player_class == 'Necromancer' else '-magefist-caster-gear-alternative'
        )
        roles = tuple(g + suffix for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        context = {'player_class': player_class}
        examples = [
            (base + '/' + str(ed), gloves(base, defense, ed), context, 'true')
            for base, defense in BASES
            for ed in (20, 30)
        ]
        item = gloves('Light Gauntlets', 12)
        examples.extend(
            (
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Amazon'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('impossible-socket', replace(item, sockets=1), context, 'false'),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                (
                    'unread-fire-skill',
                    replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 126), complete=False),
                    context,
                    'true',
                ),
            )
        )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            fire_credit = fire and label != 'unread-fire-skill'
            if truth == 'true':
                keys = ['105:0', '27:0'] + (['126:1'] if fire_credit else [])
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({k: IsPartialDict(configuration_ids=Contains(*configs)) for k in keys})
                )
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                ed = next(value for stat, _, value in candidate.raw_stats if stat == 16)
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=16, layer=0),
                            roll_range=IsPartialDict(min=20, max=30),
                            roll_quality='perfect' if ed == 30 else 'low',
                        )
                    )
                )
            absent = dict.fromkeys(('48:0', '49:0', '16:0', '31:0'), configs)
            if not fire_credit:
                absent['126:1'] = configs
            yield Case(
                id=f'magefist-caster-tables/{group}/{label}',
                item=candidate,
                context=loadout,
                scenario='unknown'
                if label == 'unread-fire-skill'
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations=absent,
                absent_configurations=() if truth == 'true' else configs,
                report_contains=('Magefist', 'Trade tier:') if truth == 'true' else ('Light Gauntlets',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/105',
                    'third-parties/d2data/json/skills.json:/74',
                    *(
                        f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__{g}.html/sections/{i}'
                        for g, i in uses
                    ),
                ),
            )


CASES = tuple(cases())
