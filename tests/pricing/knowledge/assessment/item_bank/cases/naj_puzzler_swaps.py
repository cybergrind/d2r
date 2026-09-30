"""Reusable Teleport swap alternatives require charges and verified equip requirements."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    ('Barbarian', (('double-throw-barbarian-guide', 8),)),
    ('Paladin', (('dream-paladin', 2),)),
    ('Warlock', (('echoing-strike-warlock-guide', 3), ('fire-warlock-guide', 3), ('mirrored-blades-warlock-guide', 3))),
    ('Druid', (('fissure-druid', 2),)),
    ('Amazon', (('lightning-fury-amazon-guide', 2), ('lightning-strike-amazon', 2), ('strafe-amazon', 3))),
    ('Necromancer', (('poison-nova-necromancer', 1), ('summoner-necromancer-guide', 1))),
)


def puzzler(charges=69):
    return Item(
        'Elder Staff',
        'set',
        "Naj's Puzzler",
        (
            (204, 54 * 64 + 11, (69 << 8) | charges),
            (1, 0, 35),
            (17, 0, 150),
            (18, 0, 150),
            (105, 0, 30),
            (50, 0, 6),
            (51, 0, 45),
            (9, 0, 70 * 256),
            (127, 0, 1),
        ),
        named_table_id=120,
        complete=True,
    )


def cases():
    for klass, sources in USES:
        roles = tuple(g + '-naj-teleport-swap' for g, _ in sources)
        configs = tuple(r + '-stats' for r in roles)
        context = {'player_class': klass, 'player_level': 78, 'player_strength': 44, 'player_dexterity': 37}
        item = puzzler()
        examples = (
            ('full', item, context, 'true', True),
            ('one-left', puzzler(1), context, 'true', True),
            ('empty', puzzler(0), context, 'true', False),
            ('unread-charges', replace(item, raw_stats=item.raw_stats[1:], complete=False), context, 'true', False),
            ('below-level', item, dict(context, player_level=77), 'true', False),
            ('below-strength', item, dict(context, player_strength=43), 'true', False),
            ('below-dexterity', item, dict(context, player_dexterity=36), 'true', False),
            ('unknown-equipment', item, {'player_class': klass}, 'true', False),
            ('wrong-class', item, dict(context, player_class='Sorceress'), 'false', False),
            ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown', False),
            ('ethereal', replace(item, ethereal=True), context, 'false', False),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown', False),
            ('unidentified', replace(item, identified=False), context, 'false', False),
        )
        for label, candidate, loadout, truth, active in examples:
            assessment = {
                'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))
            }
            if active:
                assessment['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            '204:3467': IsPartialDict(configuration_ids=Contains(*configs), roll_quality='unassessed'),
                        }
                    )
                )
            yield Case(
                id=f'naj-puzzler/{klass}/{label}',
                item=candidate,
                context=loadout,
                covers=roles,
                scenario='positive'
                if active
                else 'unknown'
                if label.startswith(('unread-', 'unknown-'))
                else 'negative',
                expected={'assessment': IsPartialDict(**assessment)},
                absent_configurations=() if active else configs,
                absent_stat_configurations=dict.fromkeys(('17:0', '18:0', '105:0', '50:0', '51:0'), configs),
                report_contains=("Naj's Puzzler", 'Teleport', 'Trade tier:') if active else (),
                evidence=(
                    "third-parties/d2data/json/setitems.json:/Naj's Puzzler",
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Weapon-Swap/{index}' for g, index in sources),
                ),
            )


CASES = tuple(cases())
