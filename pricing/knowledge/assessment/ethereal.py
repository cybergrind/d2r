"""Reviewed ethereal preferences, not price multipliers or zero-value verdicts."""

from pricing.knowledge.assessment.base_use import BASE_QUALITIES, MERC_WORDS, recipe_index


# Source-specific rules are deliberately explicit: caster weapons, mixed-use
# armor and unknown items must not inherit a blanket ethereal penalty.
UNIQUE_PREFERENCES = {
    "Andariel's Visage": ('preferred', 'Mercenary defense premium.', 'wp-i-uniques-misc.json/UQ-andariel-s-visage'),
    "Titan's Revenge": (
        'preferred',
        'Physical damage premium with replenishing quantity.',
        'wp-i-uniques-misc.json/UQ-titan-s-revenge',
    ),
    'Sandstorm Trek': ('preferred', 'Extra defense with self-repair.', 'wp-i-uniques-misc.json/UQ-sandstorm-trek'),
    "The Reaper's Toll": (
        'preferred',
        'Physical damage premium for the mercenary.',
        'wp-a-builds.json/ethereal Reaper',
    ),
    'War Traveler': (
        'avoid',
        'Player boots cannot be repaired when ethereal or socketed with Zod.',
        'wp-i-uniques-misc.json/UQ-war-traveler',
    ),
    'Arachnid Mesh': (
        'avoid',
        'Player belt cannot be repaired when ethereal or socketed with Zod.',
        'wp-i-uniques-misc.json/UQ-arachnid-mesh',
    ),
    'Chance Guards': (
        'avoid',
        'Player gloves cannot be repaired when ethereal or socketed with Zod.',
        'wp-i-uniques-misc.json/UQ-chance-guards',
    ),
    'Magefist': (
        'avoid',
        'Player gloves cannot be repaired when ethereal or socketed with Zod.',
        'wp-i-uniques-misc.json/UQ-magefist',
    ),
}


def _general_preference(facts):
    if facts.rarity in ('low_quality', 'low quality'):
        # Normalization creates a new item; its ethereal state is not observed.
        return None
    if facts.ethereal is None or facts.identified is not True:
        return None
    if facts.rarity == 'unique' and facts.name in UNIQUE_PREFERENCES:
        preference, reason, source = UNIQUE_PREFERENCES[facts.name]
        if preference == 'avoid':
            if not facts.capture_complete:
                return None
            # Native indestructible/self-repair exceptions override a generic
            # durability disadvantage, including socket-granted indestructible.
            if any(facts.stats.get(f'{stat}:0', {}).get('raw', 0) > 0 for stat in (152, 252)):
                return None
        return {'preference': preference, 'reason': reason, 'source': 'pricing/data/' + source}
    if facts.item_type not in ('pole', 'spea'):
        return None
    if facts.runeword:
        if facts.runeword not in MERC_WORDS:
            return None
    elif facts.rarity not in BASE_QUALITIES or facts.socket_contents != 'empty':
        return None
    if facts.base_name == 'Cryptic Axe' and facts.sockets in (0, 4, 5):
        return {
            'preference': 'preferred',
            'reason': 'Ethereal damage premium for a mercenary runeword base.',
            'source': 'pricing/data/wp-g-bases.json/BS-cryptic-axe',
        }
    for row in recipe_index().by_base.get(facts.base_name, ()):
        details = row.get('details', {})
        context = details.get('context', {})
        if (
            row.get('name') == facts.base_name
            and details.get('recommended')
            and context.get('base_tier') == 'elite'
            and context.get('builds_merc')
            and details.get('runeword') in MERC_WORDS
            and (not facts.runeword or facts.runeword == details['runeword'])
            and facts.sockets in (0, row.get('sockets'))
        ):
            return {
                'preference': 'preferred',
                'reason': 'Ethereal damage premium for an elite mercenary runeword base.',
                'source': 'pricing/data/appraisal-utility.json/' + row['source_locator'],
            }
    return None


def ethereal_preference(facts, *, roles=(), base_uses=()):
    """Keep use-specific preferences; conflicting uses leave the global line neutral."""
    from pricing.knowledge.assessment.adapters.roles import ethereal_role_input
    from pricing.knowledge.assessment.domain.roles import RoleAssessment

    if facts.ethereal is None or facts.identified is not True:
        return None
    general = _general_preference(facts)
    uses = []
    role_inputs = (ethereal_role_input(r) if isinstance(r, RoleAssessment) else r for r in roles)
    candidates = [r for r in role_inputs if r.get('status') in ('matched', 'partial')]
    candidates += [
        r
        for r in base_uses
        if r.get('status')
        in ('ready', 'preferred base', 'usable alternative', 'perfect preferred base', 'needs sockets')
    ]
    for role in candidates:
        preference = role.get('ethereal_preference')
        if not preference or preference.get('preference') not in ('preferred', 'avoid', 'neutral'):
            continue
        uses.append(
            {
                **{
                    k: role[k]
                    for k in ('id', 'build', 'variant', 'side', 'role', 'runeword', 'source', 'sources')
                    if k in role
                },
                **preference,
            }
        )
    if not uses:
        return general
    directions = {use['preference'] for use in uses}
    if general:
        directions.add(general['preference'])
    if len(directions) > 1:
        return {
            'preference': 'mixed',
            'reason': 'Ethereal preference differs between uses.',
            'uses': uses,
            'general': general,
        }
    return {'preference': next(iter(directions)), 'reason': uses[0]['reason'], 'uses': uses, 'general': general}
