"""Farming armor alternatives preserve low rolls and require ethereal self-repair evidence."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'tarnhelm-caster-progression-alternative',
        Item('Skull Cap', 'unique', 'Tarnhelm', ((127, 0, 1), (80, 0, 25), (79, 0, 75))),
        ('127:0', '80:0'),
        ('Sallet', 'Hydraskull'),
    ),
    (
        'skullder-body-armor-utility-alternative',
        Item(
            'Russet Armor',
            'unique',
            "Skullder's Ire",
            ((127, 0, 1), (240, 0, 10), (35, 0, 10), (16, 0, 160), (252, 0, 20)),
        ),
        ('127:0', '240:0', '35:0'),
        ('Balrog Skin',),
    ),
)


def cases():
    context = {'player_class': 'Barbarian'}
    for slug, item, keys, upgrades in SPECS:
        role = 'berserk-barbarian-' + slug
        repairable = item.name == "Skullder's Ire"
        maxima = {16: 200} if repairable else {80: 50}
        rows = [
            ('minimum', item, context, 'true'),
            (
                'maximum',
                replace(item, raw_stats=tuple((s, layer, maxima.get(s, v)) for s, layer, v in item.raw_stats)),
                context,
                'true',
            ),
            ('socketed-empty', replace(item, sockets=1), context, 'true'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown' if repairable else 'true'),
            ('ethereal', replace(item, ethereal=True), context, 'true' if repairable else 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        ]
        rows += [(base, replace(item, base=base), context, 'true') for base in upgrades]
        if repairable:
            rows += [
                (
                    'ethereal-unread-repair',
                    replace(item, ethereal=True, raw_stats=tuple(r for r in item.raw_stats if r[0] != 252)),
                    context,
                    'unknown',
                ),
                (
                    'ethereal-absent-repair',
                    replace(
                        item, ethereal=True, complete=True, raw_stats=tuple(r for r in item.raw_stats if r[0] != 252)
                    ),
                    context,
                    'false',
                ),
                ('level-99', replace(item, viewer_level=99), context, 'true'),
            ]
        for label, candidate, loadout, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'berserk/mf-armor/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations={'16:0': (role + '-stats',)},
                report_contains=('Trade tier:',) if candidate.identified else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/berserk-barbarian/slots',
                    'third-parties/d2data/json/uniqueitems.json',
                ),
            )


CASES = tuple(cases())
