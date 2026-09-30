"""Link an exact player or mercenary passage to an already reviewed variant component."""

from pricing.knowledge.assessment.maintenance.source_matching import requires_eq
from pricing.knowledge.assessment.maintenance.variant_mercenary_choices import required_choice


def matches(branch, role, occurrence, quote):
    if role.get('side') == 'player':
        return branch.get('player_class') == occurrence.get('class') and requires_eq(
            role.get('must', {}), 'context_eq', 'player_class', occurrence.get('class')
        )
    if role.get('side') != 'merc':
        return False
    conditions = {
        'all': [role.get('must', {}), *(d['when'] for d in role.get('depends_on', []) if d.get('required', True))]
    }
    mercenary = branch.get('mercenary_type')
    choices = branch.get('mercenary_choices')
    bounded = (
        (
            isinstance(choices, list)
            and len(choices) > 1
            and mercenary in choices
            and len(set(choices)) == len(choices)
            and required_choice(conditions, choices)
        )
        if choices is not None
        else requires_eq(conditions, 'context_eq', 'mercenary_type', mercenary)
    )
    return (
        branch.get('player_class') == occurrence.get('class')
        and isinstance(mercenary, str)
        and bool(mercenary)
        and mercenary in quote
        and requires_eq(role.get('must', {}), 'context_eq', 'player_class', occurrence.get('class'))
        and bounded
    )


def validate_primary(role, occurrence, quote, reference):
    source = role['source']
    prefix = f'/{occurrence["build"]}/variants/'
    suffix = source.get('locator', '').removeprefix(prefix)
    if (
        source.get('path') != 'pricing/data/wp-a-builds.json'
        or not source.get('locator', '').startswith(prefix)
        or not suffix.isdecimal()
        or str(int(suffix)) != suffix
    ):
        raise ValueError('variant prose source must identify one exact primary variant')
    primary = reference(source)
    build = reference({**source, 'locator': '/' + occurrence['build']})
    if (
        build.get('class') != occurrence.get('class')
        or primary.get('name') != role.get('variant')
        or quote not in primary.get('quotes', [])
        or not any(
            label == occurrence['name'] or label.startswith(occurrence['name'] + ' ')
            for label in primary.get(role['side'], {}).get(role['slot'], [])
        )
    ):
        raise ValueError('variant prose quote, class, variant or equipment differs')
