"""Five explicit Berserk sword alternatives; source base and durability stay distinct."""

from dataclasses import replace

from dirty_equals import Contains, FunctionCheck, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.zeal_combat_words import WORDS
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BASES = {'grief': ('Phase Blade', 'Zweihander'), 'oath': ('Highland Blade', 'Cryptic Sword', 'Balrog Blade')}


def cases():
    context = {'player_class': 'Barbarian'}
    for word, name, _, ethereal, sockets, _, raw, _ in WORDS:
        if word not in BASES:
            continue
        keys = ('111:0', '93:0', '141:0', '115:0', '116:0') if word == 'grief' else (
            '17:0', '93:0', '147:0', '121:0', '123:0'
        )
        maximum = {111: 400, 93: 40} if word == 'grief' else {17: 340, 18: 340, 147: 15}
        for base in BASES[word]:
            slug = base.lower().replace(' ', '-')
            role = f'berserk-barbarian-{word}-{slug}-combat-word-alternative'
            for quality in ('normal', 'superior', 'low_quality'):
                item = Item(base, quality, name, raw, ethereal=ethereal, sockets=sockets,
                            socket_contents='filled', runeword=name)
                rows = [
                    ('minimum', item, context, 'true'),
                    ('maximum', replace(item, raw_stats=tuple(
                        (s, layer, maximum.get(s, v)) for s, layer, v in raw
                    )), context, 'true'),
                    ('uncited-base', replace(item, base='Berserker Axe'), context, 'absent'),
                    ('empty', replace(item, socket_contents='empty'), context, 'false'),
                    ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
                    ('wrong-count', replace(item, sockets=sockets - 1), context, 'false'),
                    ('unknown-count', replace(item, sockets=None), context, 'unknown'),
                    ('unidentified', replace(item, identified=False), context, 'false'),
                    ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                    ('unknown-class', item, {}, 'unknown'),
                ]
                if word == 'oath':
                    rows += [
                        ('nonethereal', replace(item, ethereal=False), context, 'true'),
                        ('unread-indestructible', replace(item, raw_stats=tuple(r for r in raw if r[0] != 152)),
                         context, 'unknown'),
                        ('absent-indestructible', replace(item, raw_stats=tuple(r for r in raw if r[0] != 152),
                                                         complete=True), context, 'false'),
                    ]
                elif base == 'Zweihander':
                    rows += [
                        ('ethereal', replace(item, ethereal=True), context, 'false'),
                        ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                    ]
                for label, candidate, loadout, truth in rows:
                    expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                    if truth == 'absent':
                        expected = {
                            'roles': FunctionCheck(lambda rows, target=role: all(r['id'] != target for r in rows))
                        }
                    if truth == 'true':
                        expected['stat_evaluation'] = IsPartialDict(annotations=IsPartialDict({
                            key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys
                        }))
                    yield Case(
                        id=f'berserk/grief-oath/{word}/{slug}/{quality}/{label}',
                        item=candidate, context=loadout, expected={'assessment': IsPartialDict(**expected)},
                        covers=(role,),
                        scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown',
                                  'absent': 'negative'}[truth],
                        absent_configurations=() if truth == 'true' else (role + '-stats',),
                        report_contains=(name,),
                        evidence=('pricing/data/wp-a-builds.json:/berserk-barbarian/slots/Weapon',
                                  'third-parties/d2data/json/runes.json'),
                    )


CASES = tuple(cases())
