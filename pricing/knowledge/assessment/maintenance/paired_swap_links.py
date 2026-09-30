"""Review the second identical Barbarian HotO swap as one item, not a pair."""

from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


KIND = 'barbarian_hoto_component'
QUALIFICATION = (
    'The cited two-weapon swap requires two actual Heart of the Oak weapons for combined +6 skills; '
    'one captured weapon establishes only its own +3.'
)


def allows_slot(review, occurrence, role):
    return (
        review.get('paired_swap') == KIND
        and role.get('side') == occurrence.get('side') == 'player'
        and role.get('slot') == 'Weapon-Swap'
        and occurrence.get('slot') == 'Off-Hand-Swap'
    )


def validate_pair(review, occurrence, role, variant, klass, label):
    if (
        not allows_slot(review, occurrence, role)
        or klass != 'Barbarian'
        or role.get('names') != ['Heart of the Oak']
        or not requires_eq(role['must'], 'context_eq', 'player_class', 'Barbarian')
        or not all(
            requires_eq(role['must'], 'fact_eq', field, value)
            for field, value in (
                ('base_code', 'fla'),
                ('runeword', 'Heart of the Oak'),
                ('sockets', 4),
                ('socket_contents', 'filled'),
            )
        )
        or QUALIFICATION not in role.get('conditions', [])
        or QUALIFICATION not in review.get('required_conditions', [])
        or variant.get('player', {}).get('Weapon-Swap') != [label]
        or variant.get('player', {}).get('Off-Hand-Swap') != [label]
    ):
        raise ValueError('Unsupported paired swap component context or qualification')
