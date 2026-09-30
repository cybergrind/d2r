"""Explicit Lore/Stealth alternatives: complete recipes and wearer-compatible bases."""

from dataclasses import replace

from dirty_equals import Contains, FunctionCheck, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'Lore',
        'Cap',
        'Diadem',
        'Wolf Head',
        ((127, 0, 1), (1, 0, 10), (41, 0, 30), (34, 0, 7), (138, 0, 2), (89, 0, 2)),
        ('127:0', '1:0', '41:0', '34:0', '138:0'),
    ),
    (
        'Stealth',
        'Leather Armor',
        'Dusk Shroud',
        'Cap',
        ((96, 0, 25), (105, 0, 25), (99, 0, 25), (2, 0, 6), (27, 0, 15), (45, 0, 30), (35, 0, 3)),
        ('96:0', '105:0', '99:0', '2:0', '27:0', '45:0', '35:0'),
    ),
)


def cases():
    context = {'player_class': 'Paladin'}
    for word, base, alternate, wrong, raw, keys in SPECS:
        role = 'blessed-hammer-paladin-' + word.lower() + '-progression-equipment'
        config = role + '-stats'
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(base, quality, word, raw, sockets=2, socket_contents='filled', runeword=word)
            for label, candidate, loadout, truth in (
                ('native', item, context, 'true'),
                ('alternate-base', replace(item, base=alternate), context, 'true'),
                ('wrong-base', replace(item, base=wrong), context, 'false'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('empty', replace(item, socket_contents='empty'), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown'), context, 'unknown'),
                ('wrong-count', replace(item, sockets=1), context, 'false'),
                ('unknown-count', replace(item, sockets=None), context, 'unknown'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
            ):
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if label == 'wrong-base':
                    expected['roles'] = FunctionCheck(lambda roles, target=role: all(r['id'] != target for r in roles))
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(config)) for key in keys}
                        )
                    )
                yield Case(
                    id=f'hammer/progression-words/{word.lower()}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (config,),
                    report_contains=(word,),
                    evidence=(
                        'pricing/data/wp-a-builds.json:/blessed-hammer-paladin/slots',
                        'third-parties/d2data/json/runes.json',
                    ),
                )


CASES = tuple(cases())
