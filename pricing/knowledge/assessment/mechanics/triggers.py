"""Verify fixed named-item procs without confusing spell level and chance."""

# Exact event/skill labels in appraisal-properties.json, reviewed 2026-09-24.
# Values are proc chances. Unmatched skill names and malformed labels stay unmapped.
MARKET_FIELDS = {
    (195, 36): '544',  # Fire Bolt: on attack
    (195, 39): '545',  # Ice Bolt: on attack
    (195, 49): '546',  # Lightning: on attack
    (195, 53): '547',  # Chain Lightning: on attack
    (195, 55): '821',  # Glacial Spike: on attack
    (195, 64): '887',  # Frozen Orb: on attack
    (195, 398): '1820',  # Flame Wave: on attack
    (196, 52): '874',  # Enchant: when you Kill an Enemy
    (197, 53): '780',  # Chain Lightning: when you Die
    (197, 56): '782',  # Meteor: when you Die
    (197, 59): '781',  # Blizzard: when you Die
    (197, 92): '784',  # Poison Nova: when you Die
    (198, 32): '876',  # Valkyrie: on striking
    (198, 36): '541',  # Fire Bolt: on striking
    (198, 42): '715',  # Static Field: on striking
    (198, 44): '742',  # Frost Nova: on striking
    (198, 45): '620',  # Ice Blast: on striking
    (198, 47): '836',  # Fire Ball: on striking
    (198, 48): '542',  # Nova: on striking
    (198, 49): '731',  # Lightning: on striking
    (198, 66): '543',  # Amplify Damage: on striking
    (198, 81): '641',  # Confuse: on striking
    (198, 82): '767',  # Life Tap: on striking
    (198, 84): '778',  # Bone Spear: on striking
    (198, 87): '640',  # Decrepify: on striking
    (198, 92): '624',  # Poison Nova: on striking
    (198, 137): '869',  # Taunt: on striking
    (198, 244): '623',  # Volcano: on striking
    (198, 245): '728',  # Tornado: on striking
    (198, 258): '1943',  # Burst of Speed: on striking
    (198, 278): '846',  # Venom: on striking
    (198, 399): '1822',  # Miasma Chain: on striking
    (199, 44): '786',  # Frost Nova: when you Level-Up
    (199, 46): '787',  # Blaze: when you Level-Up
    (199, 48): '785',  # Nova: when you Level-Up
    (201, 17): '877',  # Slow Missiles: when struck
    (201, 38): '433',  # Charged Bolt: when struck
    (201, 44): '434',  # Frost Nova: when struck
    (201, 46): '700',  # Blaze: when struck
    (201, 48): '435',  # Nova: when struck
    (201, 52): '791',  # Enchant: when struck
    (201, 54): '719',  # Teleport: when struck
    (201, 55): '792',  # Glacial Spike: when struck
    (201, 62): '696',  # Hydra: when struck
    (201, 66): '812',  # Amplify Damage: when struck
    (201, 68): '808',  # Bone Armor: when struck
    (201, 71): '687',  # Dim Vision: when struck
    (201, 76): '647',  # Iron Maiden: when struck
    (201, 77): '746',  # Terror: when struck
    (201, 87): '1815',  # Decrepify: when struck
    (201, 91): '751',  # Lower Resist: when struck
    (201, 92): '686',  # Poison Nova: when struck
    (201, 121): '706',  # Fist of the Heavens: when struck
    (201, 130): '870',  # Howl: when struck
    (201, 267): '763',  # Fade: when struck
    (201, 387): '1883',  # Psychic Ward: when struck
    (201, 393): '1946',  # Sigil: Lethargy: when struck
    (201, 394): '1817',  # Ring of Fire: when struck
    (201, 400): '1948',  # Sigil: Death: when struck
}


def named_trigger_properties(facts, definition):
    if facts.name == 'Rainbow Facet':
        return {}, set(), []  # Existing variant-specific event rules own facets.
    properties, consumed, gaps = {}, set(), []
    for effect in definition.get('fixed_triggers', ()):
        stat, skill, level, chance = (effect[k] for k in ('stat_id', 'skill_id', 'level', 'chance'))
        key = f'{stat}:{skill * 64 + level}'
        row = facts.stats.get(key, {})
        if (
            row.get('status') != 'decoded'
            or row.get('unit') != 'percent_chance'
            or type(row.get('raw')) is not int
            or row['raw'] != chance
            or type(row.get('value')) not in (int, float)
            or row['value'] != chance
        ):
            gaps.append(f'Named fixed trigger {key} is missing, changed or unverified.')
            continue
        prop = MARKET_FIELDS.get((stat, skill))
        if row.get('market_property') not in (None, prop):
            gaps.append(f'Named fixed trigger {key} has an unverified market projection.')
            continue
        if prop:
            if prop in properties and properties[prop] != chance:
                gaps.append(f'Named triggers conflict on market property {prop}.')
                continue
            properties[prop] = chance
        # Identity fixes this exact event, skill, level and chance. A missing
        # market field does not turn a verified invariant into a variable roll.
        # Unknown extra listing fields still fail exact comparison downstream.
        consumed.add(key)
    return properties, consumed, gaps
