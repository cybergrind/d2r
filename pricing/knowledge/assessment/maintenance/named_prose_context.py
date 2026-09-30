"""Reviewed named-use instructions that are not repeated planner-item references."""

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


BONE_UBERS = "Along with Bone Break, Decrepify also allows you destroy Uber Baal's Physical Immune summons."


def cta_instruction(quote):
    return all(token in quote for token in ('Call to Arms', 'Battle Command', 'Battle Orders')) and any(
        token in quote.lower() for token in ('buffing yourself', 'casting battle command')
    )


def branch_matches(branch, role, occurrence, quote):
    klass = branch.get('player_class')
    if not (
        klass in CLASS_NAMES
        and klass == occurrence.get('class')
        and requires_eq(role.get('must', {}), 'context_eq', 'player_class', klass)
        and isinstance(branch.get('configuration_review'), str)
        and bool(branch['configuration_review'].strip())
    ):
        return False
    if occurrence['name'] == 'Call to Arms':
        return (
            occurrence['side'] == 'player'
            and role['slot'] == 'Weapon-Swap'
            and {'97:149', '97:155'} <= set(role.get('important_stats', []))
            and cta_instruction(quote)
        )
    if occurrence['name'] == 'Bone Break':
        supported = (
            ('Physical Damage' in quote and 'when using Bone Break' in quote)
            or 'Bone Break sets all Immune to Physical monsters to 95% Physical Resistance' in quote
            or BONE_UBERS in quote
        )
        return (
            role['slot'] in ('Charms', 'Unique Charms')
            and supported
            and (occurrence['side'] == 'player' or BONE_UBERS in quote)
        )
    if occurrence['name'] == "Butcher's Pupil":
        base = branch.get('upgrade_base_code')
        return (
            occurrence['side'] == 'player'
            and role['slot'] == 'Weapon'
            and "An Upgraded Butcher's Pupil is a strong" in quote
            and isinstance(base, str)
            and bool(base)
            and any(
                requires_eq(row.get('when', {}), 'fact_eq', 'base_code', base) for row in role.get('depends_on', [])
            )
        )
    return False


def validate_primary(role, occurrence, primary):
    if not isinstance(primary, dict):
        raise ValueError('source-context named prose needs a reviewed primary source')
    if occurrence['name'] == 'Call to Arms':
        if primary.get('label') == 'Call to Arms' or cta_instruction(primary.get('text', '')):
            return
    elif occurrence['name'] == 'Bone Break':
        if primary.get('label') == 'Bone Break' or 'Bone Break' in primary.get('text', ''):
            return
    else:
        quote = "Butcher's Pupil (Upgraded)"
        if quote in primary.get('text', '') and quote in role['source'].get('quotes', []):
            return
    raise ValueError('source-context named prose primary source does not support the named use')
