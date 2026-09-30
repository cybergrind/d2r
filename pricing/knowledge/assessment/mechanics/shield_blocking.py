"""Project native shield blocking totals into the market's bonus-only property."""

from dataclasses import replace

from pricing.knowledge.definition_store import catalog


BLOCK_PROPERTY = '446'
BLOCK_STAT = '20:0'


def modifier_blocking(facts, properties, gaps):
    base = catalog().shield_base_blocks.get(facts.base_code)
    if base is None:
        gaps.append('Native base blocking is unavailable or inconsistent for this shield.')
        return
    row = facts.stats.get(BLOCK_STAT)
    if row is None and base == 0 and facts.capture_complete and BLOCK_PROPERTY not in properties:
        return
    if row is None or row.get('status') != 'decoded' or type(row.get('value')) is not int:
        gaps.append('Shield blocking total is not fully decoded.')
        return
    total = row['value']
    if total < base or properties.get(BLOCK_PROPERTY) != total:
        gaps.append('Shield blocking total conflicts with its native base or projected property.')
        return
    bonus = total - base
    if bonus:
        properties[BLOCK_PROPERTY] = bonus
    else:
        properties.pop(BLOCK_PROPERTY, None)


def modifier_facts(facts):
    """Local named/recipe modifier view; original capture values remain intact."""
    properties, gaps = dict(facts.properties), []
    modifier_blocking(facts, properties, gaps)
    if gaps:
        return None, gaps
    stats = dict(facts.stats)
    if BLOCK_STAT in stats:
        stats[BLOCK_STAT] = {**stats[BLOCK_STAT], 'value': properties.get(BLOCK_PROPERTY, 0)}
    return replace(facts, stats=stats, properties=properties), []
