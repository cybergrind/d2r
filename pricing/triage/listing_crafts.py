"""Recover caster crafts filed under the legacy Traderie rare selector."""

from functools import lru_cache

from inventory_tracking.items.metadata import metadata, metadata_generation


@lru_cache(maxsize=2)
def amulet_code(generation):
    return next(base['code'] for base in metadata()['bases'].values() if base['name'] == 'Amulet')


def caster_amulet(row):
    """Require the whole fixed recipe and an impossible ordinary rare FCR roll.

    cubemain.json: caster amulet adds 5-10 FCR, 10-20 mana, 4-10 mana regen.
    magicsuffix.json: amulets get Apprentice (10), never Magus (20).
    Thus 15-20 FCR plus both craft stats identifies the stacked recipe.
    This rule is never applied to captured item-quality flags.
    """
    if (
        row.get('rarity') != 'rare'
        or row.get('name') != 'Amulet'
        or row.get('base_code') not in (None, amulet_code(metadata_generation()))
    ):
        return False
    props = row.get('properties', {})
    fcr, mana, regen = (props.get(key) for key in ('520', '400', '569'))
    return all(type(v) is int for v in (fcr, mana, regen)) and 15 <= fcr <= 20 and mana >= 10 and 4 <= regen <= 10
