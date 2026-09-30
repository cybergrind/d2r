"""Thundergod defensive alternatives distinguish flat absorb, cap and Amazon skills."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Paladin': (
        ('blessed-hammer-paladin', 3),
        ('dream-paladin', 4),
        ('fist-of-the-heavens-paladin', 2),
        ('smite-paladin', 0),
    ),
    'Barbarian': (('double-throw-barbarian-guide', 4),),
    'Assassin': (('dragon-talon-assassin', 1),),
    'Sorceress': (('enchant-sorceress', 4), ('lightning-sorceress', 3)),
    'Druid': (('fissure-druid', 2),),
    'Amazon': (('lightning-fury-amazon-guide', 2), ('lightning-strike-amazon', 0)),
    'Necromancer': (('poison-nova-necromancer', 3),),
}
SUFFIX = '-thundergod-s-vigor-defensive-alternative'


def belt(base, ed=160):
    return Item(
        base,
        'unique',
        "Thundergod's Vigor",
        (
            (201, 121 * 64 + 7, 5),
            (50, 0, 1),
            (51, 0, 50),
            (42, 0, 10),
            (145, 0, 20),
            (16, 0, ed),
            (3, 0, 20),
            (0, 0, 20),
            (107, 34, 3),
            (107, 35, 3),
        ),
        complete=True,
    )


def cases():
    for player_class, uses in USES.items():
        roles = tuple(g + SUFFIX for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        skill_configs = {
            skill: tuple(g + SUFFIX + '-stats' for g, _ in uses if g == guide)
            for skill, guide in (
                (34, 'lightning-strike-amazon'),
                (35, 'lightning-fury-amazon-guide'),
            )
        }
        context = {'player_class': player_class}
        examples = [
            (base + '/' + str(ed), belt(base, ed), context, 'true')
            for base in ('War Belt', 'Colossus Girdle')
            for ed in (160, 200)
        ]
        item = belt('War Belt')
        examples.extend(
            (
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Warlock'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('impossible-socket', replace(item, sockets=1), context, 'false'),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                (
                    'unread-absorb',
                    replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 145), complete=False),
                    context,
                    'true',
                ),
            )
        )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                keys = ['42:0', '0:0', '3:0'] + ([] if label == 'unread-absorb' else ['145:0'])
                annotations = {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in keys}
                annotations.update(
                    {
                        f'107:{skill}': IsPartialDict(configuration_ids=Contains(*ids))
                        for skill, ids in skill_configs.items()
                        if ids
                    }
                )
                expected['stat_evaluation'] = IsPartialDict(annotations=IsPartialDict(annotations))
                values = {'42:0': IsPartialDict(value=10)}
                if label != 'unread-absorb':
                    values['145:0'] = IsPartialDict(value=20)
                expected['facts'] = IsPartialDict(stats=IsPartialDict(values))
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                ed = next(v for stat, _, v in candidate.raw_stats if stat == 16)
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=16, layer=0),
                            roll_range=IsPartialDict(min=160, max=200),
                            roll_quality='perfect' if ed == 200 else 'low',
                        )
                    )
                )
            absent = dict.fromkeys(('16:0', '50:0', '51:0', '201:7751'), configs)
            for skill, ids in skill_configs.items():
                absent[f'107:{skill}'] = tuple(c for c in configs if c not in ids)
            if label == 'unread-absorb':
                absent['145:0'] = configs
            yield Case(
                id=f'thundergod-alternatives/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario='unknown'
                if label == 'unread-absorb'
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations=absent,
                absent_configurations=() if truth == 'true' else configs,
                report_contains=(item.name, 'Trade tier:') if truth == 'true' else (candidate.base,),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/246',
                    'third-parties/d2data/json/skills.json:/34',
                    'third-parties/d2data/json/skills.json:/35',
                    'third-parties/d2data/json/skills.json:/121',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Belts/{i}' for g, i in uses),
                ),
            )


CASES = tuple(cases())
