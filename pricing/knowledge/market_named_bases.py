"""Resolve named equipment listing bases from listing tiers or a sole elite definition."""

from pricing.knowledge.assessment.mechanics.base_tiers import base_at_tier, base_tier
from pricing.knowledge.definition_store import catalog


def resolve_equipment_base(row):
    quality = {'unique': 'unique', 'uniques': 'unique', 'set': 'set', 'sets': 'set'}.get(row.get('category'))
    tier = row.get('properties', {}).get('930')
    if quality is None:
        return
    try:
        definitions = catalog()
    except OSError, ValueError, KeyError, TypeError:
        row.setdefault('mechanics_conflicts', []).append('Named base definitions are unavailable.')
        return
    variants = definitions.named_variants.get((quality, row.get('name')), ())
    if not variants:
        return
    tier_source = 'listing'
    if '930' not in row.get('properties', {}):
        originals = {code for variant in variants for code in variant.get('base_codes', ())}
        if len(originals) != 1 or any(not variant.get('base_codes') for variant in variants):
            return
        original = next(iter(originals))
        original_tier = base_tier(original)
        if original_tier == 'Elite':
            tier, tier_source = 'Elite', 'sole_elite_definition'
        elif original_tier in ('Normal', 'Exceptional') and type(row['properties'].get('1216')) is bool:
            tier = tier_from_upgrade_flag(original, row['properties']['1216'])
            if tier is None:
                return
            tier_source = 'explicit_upgrade_flag'
        else:
            return
    codes = {base_at_tier(code, tier) for variant in variants for code in variant.get('base_codes', ())}
    if None in codes or len(codes) != 1:
        row.setdefault('mechanics_conflicts', []).append('Named listing base tier is impossible or ambiguous.')
        return
    code = next(iter(codes))
    if row.get('base_code') not in (None, code):
        row.setdefault('mechanics_conflicts', []).append('Named listing base code conflicts with its explicit tier.')
        return
    row['base_code'] = code
    upgrade_states = {original != code for variant in variants for original in variant.get('base_codes', ())}
    if len(upgrade_states) == 1:
        row['base_upgrade'] = next(iter(upgrade_states))
    if '1216' in row['properties']:
        flag = row['properties']['1216']
        if type(flag) is not bool or row.get('base_upgrade') is not flag:
            row.setdefault('mechanics_conflicts', []).append('Upgraded flag conflicts with the named base tier.')
    row.setdefault('facet_basis', {})['base_code'] = {
        'kind': 'named_base_tier',
        'tier': tier,
        'tier_source': tier_source,
        'definition_generation': definitions.generation,
        'catalog_path': 'pricing/data/appraisal-catalog.json',
    }


def tier_from_upgrade_flag(original, upgraded):
    """An explicit flag narrows the native chain, without inventing an upgrade stage."""
    if not upgraded:
        return base_tier(original)
    targets = {
        tier
        for tier in ('Normal', 'Exceptional', 'Elite')
        if (code := base_at_tier(original, tier)) is not None and code != original
    }
    return next(iter(targets)) if len(targets) == 1 else None
