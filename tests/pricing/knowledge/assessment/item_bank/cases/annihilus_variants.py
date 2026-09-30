"""Explicit valuable inventory charm occurrences across gathered build variants."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.annihilus_tables import ATTRIBUTES, RESISTS, charm
from tests.pricing.knowledge.assessment.item_bank.models import Case


# Reviewed source variants, independent of generated profile and configuration tables.
USES = {
    'Sorceress': (
        ('meteor-sorceress', ((1, 'meteor-standard'), (2, 'meteor-mf'), (3, 'meteor-set'), (4, 'meteor-ubers'))),
        ('lightning-sorceress', ((1, 'lightning-standard'), (2, 'lightning-mf'), (3, 'lightning-ubers'))),
        ('enchant-sorceress', (1, 2, 3)),
        ('nova-sorceress-guide', (1, 2, 3)),
    ),
    'Barbarian': (('double-throw-barbarian-guide', (1, 2)), ('gold-find-barbarian', (1, 2, 3, 4))),
    'Assassin': (
        ('dragon-talon-assassin', (1,)),
        ('fire-blast-assassin', (1, 2)),
        ('lightning-sentry-assassin', (1, 2)),
        ('wake-of-fire-assassin', (1, 3)),
    ),
    'Paladin': (('dream-paladin', (0, 1, 2)), ('fist-of-the-heavens-paladin', (2, 3, 4)), ('smite-paladin', (1, 2))),
    'Warlock': (
        ('echoing-strike-warlock-guide', (1, 2, 3)),
        ('fire-warlock-guide', (1, 2)),
        ('mirrored-blades-warlock-guide', (1, 2)),
    ),
    'Druid': (('fissure-druid', (1, 2)),),
    'Amazon': (
        ('lightning-fury-amazon-guide', (1, 2, 3)),
        ('lightning-strike-amazon', (1, 2)),
        ('strafe-amazon', (1, 2)),
    ),
    'Necromancer': (('poison-nova-necromancer', (1, 2, 5)), ('summoner-necromancer-guide', (1, 2))),
}


def role_rows(uses):
    for guide, variants in uses:
        for variant in variants:
            index, prefix = variant if isinstance(variant, tuple) else (variant, f'{guide}-{variant}')
            yield prefix + '-annihilus', f'pricing/data/wp-a-builds.json:/{guide}/variants/{index}/player/Charms'


def cases():
    for player_class, uses in USES.items():
        rows = tuple(role_rows(uses))
        roles = tuple(role for role, _ in rows)
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': player_class}
        item = charm()
        unread = replace(item, raw_stats=tuple(r for r in item.raw_stats if r[0] != 85), complete=False)
        examples = (
            ('minimum', item, context, 'true'),
            ('perfect', charm(20, 20, 10), context, 'true'),
            ('attributes-perfect', charm(20, 10, 5), context, 'true'),
            ('resistance-perfect', charm(10, 20, 5), context, 'true'),
            ('experience-perfect', charm(10, 10, 10), context, 'true'),
            ('unread-experience', unread, context, 'true'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Paladin' if player_class != 'Paladin' else 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                keys = (127, *ATTRIBUTES, *RESISTS, *((85,) if label != 'unread-experience' else ()))
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {f'{stat}:0': IsPartialDict(configuration_ids=Contains(*configs)) for stat in keys}
                    )
                )
            yield Case(
                id=f'annihilus-variants/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario='unknown'
                if label == 'unread-experience'
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected={'assessment': IsPartialDict(**expected)},
                absent_stat_configurations={'85:0': configs} if label == 'unread-experience' else {},
                absent_configurations=() if truth == 'true' else configs,
                report_contains=('Annihilus', 'Trade tier:') if truth == 'true' else ('Small Charm',),
                evidence=('third-parties/d2data/json/uniqueitems.json:/381', *(source for _, source in rows)),
            )


CASES = tuple(cases())
