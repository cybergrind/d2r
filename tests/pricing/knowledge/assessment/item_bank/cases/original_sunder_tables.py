"""Original sunder specimens keep their identity, beneficiary and native immunity effect."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('dream-paladin', 'Paladin', 'Flame Rift', 189, 39, -70),
    ('lightning-sorceress', 'Sorceress', 'Crack of the Heavens', 190, 41, -70),
    ('dream-paladin', 'Paladin', 'Bone Break', 192, 36, -10),
    ('dream-paladin', 'Paladin', 'Crack of the Heavens', 190, 41, -70),
    ('poison-nova-necromancer', 'Necromancer', 'Bone Break', 192, 36, -10),
    ('poison-nova-necromancer', 'Necromancer', 'Flame Rift', 189, 39, -70),
    ('double-throw-barbarian-guide', 'Barbarian', 'Bone Break', 192, 36, -10),
    ('lightning-strike-amazon', 'Amazon', 'Crack of the Heavens', 190, 41, -70),
    ('poison-nova-necromancer', 'Necromancer', 'Rotting Fissure', 191, 45, -70),
)


def cases():
    for build, cls, name, effect, penalty, roll in SPECS:
        role = build + '-' + name.lower().replace(' ', '-') + '-original-sunder-alternative'
        item = Item('Grand Charm', 'unique', name, ((effect, 0, 300), (penalty, 0, roll)))
        for label, candidate, klass, valid in (
            ('native', item, cls, True),
            ('wrong-class', item, 'Warlock', False),
            ('unknown-class', item, None, False),
            ('wrong-effect', replace(item, raw_stats=((effect, 0, 299), (penalty, 0, roll))), cls, False),
            ('unknown-effect', replace(item, raw_stats=((penalty, 0, roll),)), cls, False),
            ('crafted-form', replace(item, rarity='crafted'), cls, False),
        ):
            yield Case(
                id=f'original-sunder-table/{build}/{name}/{label}',
                item=candidate,
                context={'player_class': klass},
                covers=(f'role:{role}:unique',),
                scenario='positive' if valid else 'unknown' if label.startswith('unknown') else 'negative',
                expected={
                    'assessment': IsPartialDict(
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {f'{effect}:0': IsPartialDict(configuration_ids=Contains(role + '-stats'))}
                            )
                        )
                    )
                }
                if valid
                else {},
                absent_configurations=() if valid else (role + '-stats',),
                evidence=(
                    f'pricing/raw/mr/guides__{build}.html:Unique Charms table',
                    'pricing/raw/mr/planners/game-data.json:uniqueItems',
                ),
            )


CASES = tuple(cases())
