"""Fire, cold and poison Colossal Jewels in reviewed caster socket recipients."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Native unique rows and itemstatcost selectors, independently checked against source tables.
JEWELS = {
    'cold': ("Protector's Frost", 'protector-s-frost', 422, 331, 335, 40, ((54, 0, 10), (55, 0, 30), (56, 0, 125))),
    'fire': ("Defender's Fire", 'defender-s-fire', 423, 329, 333, 46, ((48, 0, 20), (49, 0, 60))),
    'poison': ("Defender's Bile", 'defender-s-bile', 420, 332, 336, 68, ((57, 0, 975), (58, 0, 975), (59, 0, 25))),
}
USES = (
    ('blizzard-sorceress', (1, 2), 'Sorceress', 'cold', 'Helmet'),
    ('enchant-sorceress', (2,), 'Sorceress', 'fire', 'Helmet'),
    ('fire-warlock-guide', (2,), 'Warlock', 'fire', 'Helmet'),
    ('meteor-sorceress', (1, 2), 'Sorceress', 'fire', 'Helmet'),
    ('poison-nova-necromancer', (1,), 'Necromancer', 'poison', 'Weapon'),
)


def jewel(element, perfect=()):
    name, _, table, mastery, pierce, proc, attack = JEWELS[element]
    ranges = ((mastery, 5, 10), (pierce, 5, 10), (85, 3, 5), (80, 15, 35), (79, 25, 50))
    return Item(
        'Colossal Jewel',
        'unique',
        name,
        (*((sid, 0, high if sid in perfect else low) for sid, low, high in ranges), *attack, (201, proc * 64 + 25, 1)),
        named_table_id=table,
        complete=True,
    )


def cases():
    for guide, variants, klass, element, slot in USES:
        name, slug, table, mastery, pierce, proc, attack = JEWELS[element]
        ranges = ((mastery, 5, 10), (pierce, 5, 10), (85, 3, 5), (80, 15, 35), (79, 25, 50))
        for variant in variants:
            role = f'{guide}-{slug}-v{variant}-{slot.lower()}-0-named-socket-jewel'
            config = role + '-stats'
            recipient = (
                "Death's Web"
                if element == 'poison'
                else "Nightwing's Veil"
                if element == 'cold' and variant == 1
                else 'Harlequin Crest'
            )
            context = {'player_class': klass, 'player_items': [recipient]}
            item = jewel(element)
            examples = [
                ('minimum', item, context, 'true', True, ()),
                (
                    'maximum',
                    jewel(element, tuple(s[0] for s in ranges)),
                    context,
                    'true',
                    True,
                    tuple(s[0] for s in ranges),
                ),
                ('mastery-only-perfect', jewel(element, (mastery,)), context, 'true', True, (mastery,)),
                ('pierce-only-perfect', jewel(element, (pierce,)), context, 'true', True, (pierce,)),
                ('wrong-class', item, dict(context, player_class='Barbarian'), 'false', False, ()),
                ('unknown-class', item, {'player_items': [recipient]}, 'unknown', False, ()),
                ('missing-recipient', item, dict(context, player_items=[]), 'true', False, ()),
                ('unknown-recipient', item, {'player_class': klass}, 'true', False, ()),
                ('unidentified', replace(item, identified=False), context, 'false', False, ()),
                ('ethereal', replace(item, ethereal=True), context, 'false', False, ()),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown', False, ()),
                ('socketed', replace(item, sockets=1), context, 'false', False, ()),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown', False, ()),
            ]
            for sid in (mastery, pierce):
                stats = tuple(s for s in item.raw_stats if s[0] != sid)
                examples.extend(
                    (
                        (f'missing-{sid}', replace(item, raw_stats=stats), context, 'false', False, ()),
                        (
                            f'unread-{sid}',
                            replace(item, raw_stats=stats, complete=False),
                            context,
                            'unknown',
                            False,
                            (),
                        ),
                    )
                )
            for label, candidate, loadout, truth, active, perfect in examples:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {f'{sid}:0': IsPartialDict(configuration_ids=Contains(config)) for sid, _, _ in ranges}
                        )
                    )
                result = {'assessment': IsPartialDict(**expected)}
                if active:
                    result['extraction'] = IsPartialDict(
                        decoded_stats=Contains(
                            *(
                                IsPartialDict(
                                    memory_stat=IsPartialDict(id=sid),
                                    roll_range=IsPartialDict(min=low, max=high),
                                    roll_quality='perfect' if sid in perfect else 'low',
                                )
                                for sid, low, high in ranges
                            )
                        )
                    )
                yield Case(
                    id=f'elemental-colossal/{role}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=(role,),
                    scenario='positive'
                    if active
                    else 'unknown'
                    if label.startswith(('unknown-', 'unread-'))
                    else 'negative',
                    expected=result,
                    absent_configurations=() if active else (config,),
                    absent_stat_configurations=dict.fromkeys(
                        (*[f'{sid}:0' for sid, _, _ in attack], f'201:{proc * 64 + 25}'), (config,)
                    ),
                    report_contains=(name,) if active else (),
                    evidence=(
                        f'third-parties/d2data/json/uniqueitems.json:/{table}',
                        f'pricing/data/wp-a-builds.json:/{guide}/variants/{variant}/player/{slot}/0',
                    ),
                )


CASES = tuple(cases())
