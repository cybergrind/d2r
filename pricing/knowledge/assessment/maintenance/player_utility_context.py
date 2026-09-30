"""Finite reviewed utility-use grammar; item names alone do not establish a role."""

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


USES = {
    'enchant_prebuff': ('Demon Limb', 'Prebuff', ('unspecified', 'Weapon-Swap')),
    'fade_prebuff': ('Treachery', 'Prebuff', ('unspecified', 'Body Armors', 'Body Armor')),
    'casting_swap': ('Wizardspike', 'Weapon-Swap', ('unspecified', 'Weapon-Swap')),
    'teleport_swap': ("Naj's Puzzler", 'Weapon-Swap', ('unspecified', 'Weapon-Swap')),
}


def passage_supports(purpose, text):
    if purpose == 'enchant_prebuff':
        return 'Demon Limb pre-buffs Enchant' in text or 'Pre-buffing Enchant with Demon Limb' in text
    if purpose == 'fade_prebuff':
        return 'Treachery pre-buffs Fade' in text or 'pre-buffing Fade with Treachery' in text
    if purpose == 'casting_swap':
        return all(
            fragment in text
            for fragment in (
                'Wizardspike is used for the Faster Cast Rate it provides on Weapon-Swap',
                'prior to acquiring a Call to Arms',
                'Barbarian-granted Battle Orders is available',
            )
        )
    if purpose == 'teleport_swap':
        return all(
            fragment in text
            for fragment in (
                "Only use Naj's Puzzler",
                'for Teleport Charges',
                'if you are not using Enigma',
            )
        )
    return False


def branch_matches(branch, role, occurrence, quote):
    purpose = branch.get('utility_kind')
    if purpose not in USES:
        return False
    name, slot, source_slots = USES[purpose]
    klass = branch.get('player_class')
    return (
        occurrence.get('name') == name
        and occurrence.get('slot') in source_slots
        and role.get('slot') == slot
        and klass in CLASS_NAMES
        and klass == occurrence.get('class')
        and requires_eq(role.get('must', {}), 'context_eq', 'player_class', klass)
        and isinstance(branch.get('configuration_review'), str)
        and bool(branch['configuration_review'].strip())
        and passage_supports(purpose, quote)
    )


def validate_primary(branch, role, primary):
    quotes = role['source'].get('quotes', [])
    if (
        not isinstance(primary, dict)
        or not isinstance(primary.get('text'), str)
        or not any(
            isinstance(quote, str) and quote in primary['text'] and passage_supports(branch.get('utility_kind'), quote)
            for quote in quotes
        )
    ):
        raise ValueError('source-context utility requires the reviewed primary use instruction')
