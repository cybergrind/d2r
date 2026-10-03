"""Echoing Ubers Sazabi pieces preserve wearer, companions and socket effects."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


PIECES = (
    ('sword', "Sazabi's Cobalt Redeemer", 'Cryptic Sword', 'Ber Rune', ((93, 0, 40), (136, 0, 20)), ('93:0', '136:0')),
    (
        'armor',
        "Sazabi's Ghost Liberator",
        'Balrog Skin',
        'Ber Rune',
        ((7, 0, 50 * 256), (99, 0, 30), (36, 0, 8)),
        ('7:0', '99:0', '36:0'),
    ),
    (
        'helm',
        "Sazabi's Mental Sheath",
        'Basinet',
        'Cham Rune',
        ((127, 0, 1), (39, 0, 15), (41, 0, 15), (153, 0, 1)),
        ('127:0', '39:0', '41:0', '153:0'),
    ),
)


def cases():
    for slug, name, base, rune, stats, keys in PIECES:
        role = 'echoing-ubers-sazabi-' + slug
        item = Item(
            base,
            'set',
            name,
            (*stats, (194, 0, 1)),
            sockets=1,
            socket_contents='filled',
            socket_items=(SocketItem(rune),),
        )
        context = {
            'player_class': 'Warlock',
            'mercenary_type': 'Act 5 Frenzy',
            'mercenary_items': [row[1] for row in PIECES if row[1] != name],
        }
        scenarios = [
            ('complete-component', item, context, 'true', True),
            ('wrong-class', item, {**context, 'player_class': 'Paladin'}, 'false', False),
            ('unknown-class', item, {**context, 'player_class': None}, 'unknown', False),
            ('wrong-mercenary', item, {**context, 'mercenary_type': 'Act 2 Might'}, 'false', False),
            ('unknown-mercenary', item, {**context, 'mercenary_type': None}, 'unknown', False),
            ('impossible-ethereal', replace(item, ethereal=True), context, 'false', False),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown', False),
            ('missing-companion', item, {**context, 'mercenary_items': context['mercenary_items'][:1]}, 'true', False),
            ('unknown-companions', item, {k: v for k, v in context.items() if k != 'mercenary_items'}, 'true', False),
            (
                'player-only-companions',
                item,
                {**context, 'mercenary_items': [], 'player_items': context['mercenary_items']},
                'true',
                False,
            ),
            ('empty-socket', replace(item, socket_contents='empty', socket_items=()), context, 'true', False),
            ('wrong-socket', replace(item, socket_items=(SocketItem('Ist Rune'),)), context, 'true', False),
            ('unknown-socket', replace(item, socket_contents='unknown', socket_items=()), context, 'true', False),
        ]
        for label, candidate, loadout, truth, active in scenarios:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            yield Case(
                id=f'echoing/sazabi/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=(role,),
                evidence=(
                    'pricing/data/wp-a-builds.json:/echoing-strike-warlock-guide/variants/3',
                    'pricing/raw/d2data/setitems.json',
                    'third-parties/d2data/json/gems.json',
                ),
                scenario='positive' if active else 'unknown' if 'unknown' in label else 'negative',
                absent_configurations=() if active else (role + '-stats',),
                # Impossible ethereal set identities are rejected by the tier policy.
                report_contains=()
                if label == 'impossible-ethereal'
                else (
                    'Trade tier:',
                    *(
                        ('    Check: ' + '; '.join(sorted(context['mercenary_items'])),)
                        if label == 'unknown-companions'
                        else ()
                    ),
                    *(('    Needs: ' + context['mercenary_items'][1],) if label == 'missing-companion' else ()),
                    *(
                        ('    Needs: ' + '; '.join(sorted(context['mercenary_items'])),)
                        if label == 'player-only-companions'
                        else ()
                    ),
                    *(
                        ('    Setup: ' + '; '.join(sorted(context['mercenary_items'])),)
                        if label == 'complete-component'
                        else ()
                    ),
                ),
            )


CASES = tuple(cases())
