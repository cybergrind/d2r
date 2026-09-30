"""Horazon standalone items and the independently qualified three-piece fire use."""

from dataclasses import replace
from itertools import combinations

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


RECIPES = (
    (
        'Countenance',
        'Demonhead',
        135,
        'Helmets/8',
        ((225, 0, 2), (83, 7, 1), (0, 0, 10), (35, 0, 7)),
        ('83:7', '0:0', '35:0'),
        ('225:0', '76:0'),
        None,
    ),
    (
        'Dominion',
        'Russet Armor',
        136,
        'Body Armors/9',
        ((188, 56, 2), (16, 0, 75), (9, 0, 75 * 256), (43, 0, 15), (39, 0, 15), (41, 0, 15)),
        ('9:0', '43:0', '39:0', '41:0', '16:0'),
        ('188:56', '45:0', '3:0', '36:0'),
        'Balrog Skin',
    ),
    (
        'Legacy',
        'Mirrored Boots',
        138,
        'Boots/7',
        ((96, 0, 30), (0, 0, 10), (2, 0, 10), (37, 0, 20), (153, 0, 1), (91, 0, -30)),
        ('96:0', '0:0', '2:0', '37:0', '153:0'),
        ('35:0',),
        None,
    ),
    (
        'Secrets',
        'Occult Codex',
        139,
        'Off-Hand/10',
        ((188, 57, 2), (99, 0, 30), (20, 0, 20), (3, 0, 20), (7, 0, 30 * 256)),
        ('99:0', '20:0', '3:0', '7:0', '333:0'),
        ('188:57', '105:0'),
        None,
    ),
)
COMPANIONS = tuple("Horazon's " + part for part in ('Countenance', 'Dominion', 'Hold', 'Legacy'))


def cases():
    for part, base, table_id, locator, raw, keys, excluded, upgraded in RECIPES:
        secret = part == 'Secrets'
        name = "Horazon's " + part
        role = (
            'fire-warlock-guide-horazon-s-'
            + part.lower()
            + ('-qualified-equipment' if secret else '-caster-remainder-alternative')
        )
        config = role + '-stats'
        original = Item(base, 'set', name, raw, named_table_id=table_id)
        ctx = {'player_class': 'Warlock'}
        if secret:
            ctx = {**ctx, 'player_items': COMPANIONS[:2]}
            original = replace(original, raw_stats=(*raw, (333, 0, 25)))
        variants = [
            ('native', original, ctx, 'true', 'true'),
            ('wrong-class', original, {**ctx, 'player_class': 'Sorceress'}, 'false', None),
            ('unknown-class', original, {k: v for k, v in ctx.items() if k != 'player_class'}, 'unknown', None),
            ('ethereal', replace(original, ethereal=True), ctx, 'false', None),
            ('unknown-ethereal', replace(original, ethereal=None), ctx, 'unknown', None),
            ('unidentified', replace(original, identified=False), ctx, 'false', None),
            ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), ctx, 'unknown', None),
            (
                'illegal-two-sockets',
                replace(original, sockets=2, raw_stats=(*original.raw_stats, (194, 0, 2))),
                ctx,
                'false',
                None,
            ),
            (
                'one-socket',
                replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))),
                ctx,
                'false' if part == 'Legacy' else 'true',
                None if part == 'Legacy' else 'true',
            ),
        ]
        if upgraded:
            variants.append(('upgraded', replace(original, base=upgraded), ctx, 'true', 'true'))
        if secret:
            variants.extend(
                (f'companion-pair-{i}', original, {**ctx, 'player_items': pair}, 'true', 'true')
                for i, pair in enumerate(combinations(COMPANIONS, 2))
            )
            for label, companions, dependency in (
                ('standalone', (), 'false'),
                ('one-companion', COMPANIONS[:1], 'false'),
                ('duplicate-companion', (COMPANIONS[0], COMPANIONS[0]), 'false'),
                ('unrelated-companions', ("Tal Rasha's Guardianship", "Trang-Oul's Wing"), 'false'),
            ):
                variants.append(
                    (label, replace(original, raw_stats=raw), {**ctx, 'player_items': companions}, 'true', dependency)
                )
            variants.append(('unknown-companions', original, {'player_class': 'Warlock'}, 'true', 'unknown'))
        for label, item, context, truth, dependency in variants:
            active = truth == dependency == 'true'
            expected_role = {'id': role, 'rule_trace': IsPartialDict(truth=truth)}
            if secret and dependency is not None:
                expected_role['dependencies'] = Contains(IsPartialDict(status=dependency))
            expected = {'roles': Contains(IsPartialDict(**expected_role))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'horazon-fire/{part.lower()}/{label}',
                item=item,
                context=context,
                covers=(role,),
                scenario='positive' if active else 'unknown' if 'unknown' in (truth, dependency) else 'negative',
                expected={'assessment': IsPartialDict(**expected)},
                absent_configurations=() if active else (config,),
                absent_stat_configurations=dict.fromkeys(excluded, (config,)),
                report_contains=(name, 'Trade tier:') if active else (),
                evidence=(
                    'pricing/data/wp-a-builds.json:/fire-warlock-guide/slots/' + locator,
                    'third-parties/d2data/json/setitems.json:/' + name,
                ),
            )


CASES = tuple(cases())
