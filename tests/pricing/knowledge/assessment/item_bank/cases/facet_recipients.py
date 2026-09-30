"""Loose elemental Facets: native variants, roll bounds and intended recipients."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.facet_shields import ELEMENTS, facet
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Each row is an independently read WP-A equipment occurrence. These are loose
# component candidates, not proof that the recipient already has a socket.
SPECS = (
    ('blizzard-sorceress', 1, 'Weapon', 'Sorceress', 'cold', "Death's Fathom"),
    ('blizzard-sorceress', 1, 'Body Armor', 'Sorceress', 'cold', "Ormus' Robes"),
    ('enchant-sorceress', 1, 'Body Armor', 'Sorceress', 'fire', 'Skin of the Vipermagi'),
    ('enchant-sorceress', 2, 'Body Armor', 'Sorceress', 'fire', 'Skin of the Vipermagi'),
    ('fire-warlock-guide', 1, 'Weapon', 'Warlock', 'fire', "Mang Song's Lesson"),
    ('fissure-druid', 3, 'Helmet', 'Druid', 'fire', 'Ravenlore'),
    ('fist-of-the-heavens-paladin', 2, 'Helmet', 'Paladin', 'lightning', "Griffon's Eye"),
    ('lightning-sorceress', 3, 'Helmet', 'Sorceress', 'lightning', "Griffon's Eye"),
    ('lightning-strike-amazon', 2, 'Helmet', 'Amazon', 'lightning', "Griffon's Eye"),
    ('meteor-sorceress', 4, 'Weapon', 'Sorceress', 'fire', "Eschuta's Temper"),
    ('nova-sorceress-guide', 1, 'Body Armor', 'Sorceress', 'lightning', 'Skin of the Vipermagi'),
    ('hydra-sorceress', 1, 'Socket filler', 'Sorceress', 'fire', None),
)


def loose(element, damage=3, pierce=3, *, up=False):
    child = facet(element, damage, up=up)
    pierce_stat = ELEMENTS[element][1]
    return Item(
        'Jewel',
        'unique',
        'Rainbow Facet',
        tuple((sid, layer, pierce if sid == pierce_stat else raw) for sid, layer, raw in child.raw_stats),
        named_table_id=child.unique_table_id,
        complete=True,
    )


def cases():
    for guide, variant, slot, klass, element, host in SPECS:
        role = (
            f'{guide}-rainbow-facet-v{variant}-{slot.lower().replace(" ", "-")}-0-named-socket-jewel'
            if host
            else 'hydra-standard-fire-facet'
        )
        config = role + '-stats'
        mastery, pierce = ELEMENTS[element][:2]
        context = (
            {'player_class': klass, 'player_items': [host]}
            if host
            else {
                'player_class': klass,
                'player_total_fcr': 105,
            }
        )
        examples = [
            (
                f'{"level-up" if up else "death"}/{damage}-{reduction}',
                loose(element, damage, reduction, up=up),
                context,
                'true',
                True,
            )
            for up in (False, True)
            for damage, reduction in ((3, 3), (3, 5), (5, 3), (5, 5))
        ]
        item = loose(element)
        examples.extend(
            (
                ('wrong-element', loose('poison'), context, 'false', False),
                ('wrong-class', item, dict(context, player_class='Barbarian'), 'false', False),
                ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown', False),
                ('unidentified', replace(item, identified=False), context, None, False),
                (
                    'unread-pierce',
                    replace(item, complete=False, raw_stats=tuple(row for row in item.raw_stats if row[0] != pierce)),
                    context,
                    'unknown',
                    False,
                ),
            )
        )
        if host:
            examples.extend(
                (
                    ('missing-recipient', item, dict(context, player_items=[]), 'true', False),
                    ('unknown-recipient', item, {'player_class': klass}, 'true', False),
                    ('ethereal-jewel', replace(item, ethereal=True), context, 'false', False),
                    ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown', False),
                    ('impossible-socket', replace(item, sockets=1), context, 'false', False),
                )
            )
        else:
            examples.extend(
                (
                    ('below-fcr', item, dict(context, player_total_fcr=104), 'true', False),
                    ('unknown-fcr', item, {'player_class': klass}, 'true', False),
                )
            )
        for label, candidate, loadout, truth, active in examples:
            expected = {}
            if truth is not None:
                expected['roles'] = Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))
            if active:
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {f'{sid}:0': IsPartialDict(configuration_ids=Contains(config)) for sid in (mastery, pierce)}
                    )
                )
            result = {'assessment': IsPartialDict(**expected)}
            if active:
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=sid),
                                roll_range=IsPartialDict(min=3, max=5),
                                roll_quality='perfect'
                                if next(raw for stat, _, raw in candidate.raw_stats if stat == sid) == 5
                                else 'low',
                            )
                            for sid in (mastery, pierce)
                        )
                    )
                )
            source = (
                f'pricing/data/wp-a-builds.json:/{guide}/variants/{variant}/player/{slot}/0'
                if host
                else 'pricing/data/appraisal-reviewed-guide-excerpts.json:/hydra-standard-fire-facet'
            )
            yield Case(
                id=f'facet-recipient/{role}/{label}',
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
                absent_stat_configurations=dict.fromkeys(('48:0', '49:0', '50:0', '51:0', '54:0', '55:0'), (config,)),
                report_contains=('Rainbow Facet',) if active else (),
                evidence=(source, f'third-parties/d2data/json/uniqueitems.json:/{candidate.named_table_id}'),
            )


CASES = tuple(cases())
