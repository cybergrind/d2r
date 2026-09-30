"""Conservative identity-only parsing of explicit named equipment socket labels."""

import re


# Exact magic-jewel labels in the cached guide equipment/prose. These establish
# the grammatical filler, not its roll, recipient suitability or trade value.
MAGIC_JEWELS = frozenset({'ruby jewel of fervor', 'jewel of fervor'})
GEM_NAMES = frozenset({'amethyst', 'diamond', 'emerald', 'ruby', 'sapphire', 'topaz', 'skull'})


def socket_context(row, suffix, catalog):
    if row.get('category') not in ('unique', 'set') or not suffix.startswith(('with ', 'socketed with ')):
        return False
    equipment_codes = {
        value.get('base_code') for value in catalog.values() if value.get('category') in ('armor', 'weapon')
    } - {None}
    if row.get('base_code') not in equipment_codes:
        return False
    jewel_codes = {
        value.get('base_code')
        for value in catalog.values()
        if value.get('category') == 'misc' and value['name'] in ('Jewel', 'Colossal Jewel')
    } - {None}
    fillers = set(MAGIC_JEWELS)
    for value in catalog.values():
        name = value['name'].casefold()
        material = value.get('category') == 'misc' and (name.endswith(' rune') or name.split()[-1] in GEM_NAMES)
        jewel = value.get('category') == 'unique' and value.get('base_code') in jewel_codes
        if material or jewel:
            fillers.update(label.casefold() for label in (value['name'], *value.get('aliases', [])))
    choices = '|'.join(re.escape(name) for name in sorted(fillers, key=lambda name: (-len(name), name)))
    part = rf'(?:(?:a|an) )?(?:[1-6]x )?(?:{choices})'
    # Parenthesized context must trail the entire payload; outside operators or
    # other equipment remain unresolved instead of becoming a single carrier.
    pattern = rf'(?:socketed )?with {part}(?: \+ {part})*(?: \([^()]*\))*'
    return re.fullmatch(pattern, suffix) is not None
