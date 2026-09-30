"""Explicit narrative-to-configuration reviews; no source context is rewritten."""

import hashlib
import json
from datetime import date

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.charm_source_context import (
    branch_matches as charm_branch_matches,
    identity_supported as charm_identity_supported,
)
from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.guide_positions import require_same_section
from pricing.knowledge.assessment.maintenance.guide_spans import occurrence_source
from pricing.knowledge.assessment.maintenance.mercenary_source_context import (
    MERCENARY_SLOTS,
    branch_matches as mercenary_branch_matches,
    corrected_prose_matches,
    support_prose_matches,
    validate_branches as validate_mercenary_branches,
)
from pricing.knowledge.assessment.maintenance.named_prose_context import (
    branch_matches as named_prose_matches,
    validate_primary as validate_named_primary,
)
from pricing.knowledge.assessment.maintenance.player_utility_context import (
    branch_matches as utility_branch_matches,
    validate_primary as validate_utility_primary,
)
from pricing.knowledge.assessment.maintenance.review_dossiers import _review_leads
from pricing.knowledge.assessment.maintenance.socket_component_context import (
    identity_matches as socket_identity_matches,
    validate_entry as validate_socket_entry,
)
from pricing.knowledge.assessment.maintenance.source_matching import occurrence_quality_matches, requires_eq
from pricing.knowledge.assessment.maintenance.variant_mercenary_choices import validate_choices
from pricing.knowledge.assessment.maintenance.variant_prose_context import (
    matches as variant_context_matches,
    validate_primary as validate_variant_primary,
)
from pricing.knowledge.assessment.policies.sources import resolve_pointer


OCCURRENCE_FIELDS = (
    'name',
    'original_label',
    'category',
    'build',
    'variant',
    'side',
    'slot',
    'source_id',
    'source_locator',
)


PLAYER_SLOTS = frozenset(
    {
        'Weapon',
        'Off-Hand',
        'Body Armor',
        'Body Armors',
        'Helmets',
        'Gloves',
        'Belts',
        'Boots',
        'Amulets',
        'Rings',
        'Weapon-Swap',
        'Off-Hand-Swap',
        'Off-Hand Swap',
        'Charms',
        'Unique Charms',
    }
)


def occurrence_context_supported(kind, occurrence):
    if not occurrence:
        return False
    if kind in ('mercenary_table_correction', 'mercenary_table_pattern_correction'):
        return (
            occurrence.get('side') == 'player'
            and occurrence.get('slot') in MERCENARY_SLOTS
            and occurrence.get('class') in CLASS_NAMES
        )
    if kind == 'qualified_named_prose':
        return (
            occurrence.get('side') in ('player', 'merc')
            and occurrence.get('slot') == 'unspecified'
            and occurrence.get('class') in CLASS_NAMES
        )
    if kind == 'player_utility_reference':
        return occurrence.get('side') == 'player' and occurrence.get('class') in CLASS_NAMES
    if kind in ('variant_player_narrative', 'variant_mercenary_narrative'):
        return (
            occurrence.get('side') == ('player' if kind == 'variant_player_narrative' else 'merc')
            and occurrence.get('slot') == 'unspecified'
            and occurrence.get('class') in CLASS_NAMES
        )
    if kind == 'mercenary_narrative':
        return occurrence.get('side') == 'merc' and occurrence.get('slot') == 'unspecified'
    if kind in (
        'mercenary_prose_correction',
        'mercenary_support_reference',
        'player_prose_repeat',
        'player_pattern_prose_repeat',
    ):
        return (
            occurrence.get('side') == 'player'
            and occurrence.get('slot') == 'unspecified'
            and occurrence.get('class') in CLASS_NAMES
        )
    if kind == 'mercenary_equipment':
        return (
            occurrence.get('side') == 'merc'
            and occurrence.get('slot') in MERCENARY_SLOTS
            and occurrence.get('class') in CLASS_NAMES
        )
    if kind in ('player_equipment', 'player_pattern', 'player_charm_pattern', 'socket_component_reference'):
        return (
            occurrence.get('side') == 'player'
            and occurrence.get('slot') in PLAYER_SLOTS
            and occurrence.get('class') in CLASS_NAMES
        )
    return False


def branch_context_matches(kind, branch, role, occurrence, quote):
    if kind in ('mercenary_table_correction', 'mercenary_table_pattern_correction'):
        return (
            branch.get('player_class') == occurrence.get('class')
            and branch.get('mercenary_type') == 'Act 2 Might'
            and role.get('slot') == occurrence.get('slot')
            and isinstance(branch.get('configuration_review'), str)
            and bool(branch['configuration_review'].strip())
            and requires_eq(role.get('must', {}), 'context_eq', 'player_class', occurrence.get('class'))
            and requires_eq(role.get('must', {}), 'context_eq', 'mercenary_type', 'Act 2 Might')
        )
    if kind == 'qualified_named_prose':
        return named_prose_matches(branch, role, occurrence, quote)
    if kind == 'player_utility_reference':
        return utility_branch_matches(branch, role, occurrence, quote)
    if kind in ('player_prose_repeat', 'player_pattern_prose_repeat'):
        klass = branch.get('player_class')
        return (
            klass == occurrence.get('class')
            and klass in CLASS_NAMES
            and role.get('slot') in PLAYER_SLOTS
            and isinstance(branch.get('configuration_review'), str)
            and bool(branch['configuration_review'].strip())
            and requires_eq(role.get('must', {}), 'context_eq', 'player_class', klass)
        )
    if kind == 'mercenary_support_reference':
        return support_prose_matches(branch, role, occurrence, quote)
    if kind == 'mercenary_prose_correction':
        return corrected_prose_matches(branch, role, occurrence, quote)
    if kind in ('variant_player_narrative', 'variant_mercenary_narrative'):
        return variant_context_matches(branch, role, occurrence, quote)
    if kind == 'mercenary_narrative':
        mercenary = branch.get('mercenary_type')
        return (
            bool(mercenary)
            and mercenary in quote
            and requires_eq(role.get('must', {}), 'context_eq', 'mercenary_type', mercenary)
        )
    klass = branch.get('player_class')
    canonical_slot = {'Body Armors': 'Body Armor', 'Off-Hand Swap': 'Off-Hand-Swap', 'Unique Charms': 'Charms'}
    same_slot = canonical_slot.get(role['slot'], role['slot']) == canonical_slot.get(
        occurrence['slot'], occurrence['slot']
    )
    return (
        kind
        in (
            'player_equipment',
            'player_pattern',
            'player_charm_pattern',
            'mercenary_equipment',
            'socket_component_reference',
        )
        and klass == occurrence.get('class')
        and klass in CLASS_NAMES
        and same_slot
        and isinstance(branch.get('configuration_review'), str)
        and bool(branch['configuration_review'].strip())
        and requires_eq(role.get('must', {}), 'context_eq', 'player_class', klass)
        and (kind != 'mercenary_equipment' or mercenary_branch_matches(branch, role, quote))
    )


def identity_context_supported(kind, occurrence):
    if kind == 'player_charm_pattern':
        return charm_identity_supported(occurrence)
    if kind == 'socket_component_reference':
        return occurrence.get('category') in ('misc', None)
    if kind in ('player_pattern', 'player_pattern_prose_repeat', 'mercenary_table_pattern_correction'):
        return occurrence.get('identity_status') == 'unresolved' and occurrence.get('category') is None
    return occurrence.get('identity_status') == 'resolved' and occurrence.get('category') in (
        'unique',
        'set',
        'runeword',
    )


def branch_identity_matches(kind, branch, role, occurrence, quote, uses):
    if kind == 'socket_component_reference':
        return socket_identity_matches(branch, role)
    if kind == 'player_charm_pattern' and not charm_branch_matches(role, occurrence):
        return False
    if kind not in (
        'player_pattern',
        'player_charm_pattern',
        'player_pattern_prose_repeat',
        'mercenary_table_pattern_correction',
    ):
        return occurrence['name'] in role.get('names', []) and occurrence_quality_matches(occurrence, role)
    return (
        not role.get('names')
        and bool(role.get('types'))
        and bool(role.get('qualities'))
        and set(role['qualities']) <= {'normal', 'superior', 'low_quality', 'magic', 'rare', 'crafted'}
        and branch.get('qualities') == role['qualities']
        and (
            (
                branch.get('pattern_label')
                if kind == 'mercenary_table_pattern_correction'
                else branch.get('source_label')
            )
            == occurrence['original_label']
            if kind in ('player_pattern_prose_repeat', 'mercenary_table_pattern_correction')
            else pattern_quote_matches(branch.get('pattern_label'), quote, role)
        )
        and any(
            use.get('pattern') == role['id']
            and use.get('profile_id') == role['id']
            and use.get('pattern_label') == branch.get('pattern_label')
            and use.get('review_state') == 'reviewed'
            and use.get('scope') == 'softcore'
            and use.get('strength') in ('required', 'alternative', 'recommended')
            for use in uses
        )
    )


def pattern_quote_matches(label, quote, role):
    if label == quote:
        return True
    return any(
        label == prefix + quote and requires_eq(role.get('must', {}), 'fact_eq', 'socket_contents', contents)
        for prefix, contents in (('Empty preparation base for ', 'empty'), ('Completed ', 'filled'))
    )


def compile_source_context_reviews(document, occurrences, profiles, uses, root):
    if document is None:
        return []
    if document.get('schema_version') != 1 or not isinstance(document.get('rows'), list):
        raise ValueError('Invalid source-context review schema')
    compile_demand(uses, profiles)
    by_occurrence = {row['id']: row for row in occurrences}
    by_profile = {row['id']: row for row in profiles}
    eligible = set(_review_leads(occurrences)['occurrence_ids'])
    endorsed = {
        row['profile_id']
        for row in uses
        if row.get('review_state') == 'reviewed'
        and row.get('scope') == 'softcore'
        and row.get('strength') in ('required', 'preferred', 'alternative', 'recommended')
    }
    cache, positions = {}, {}

    def reference(ref):
        path = (root / ref['path']).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError('Missing source-context evidence')
        key = ref['path'], ref['sha256']
        if key not in cache:
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != ref['sha256']:
                raise ValueError('Stale source-context evidence')
            cache[key] = json.loads(raw)
        return resolve_pointer(cache[key], ref['locator'])

    result, seen_ids, seen_occurrences = [], set(), set()
    for index, review in enumerate(document['rows']):
        identity, oid = review['id'], review['occurrence_id']
        if identity in seen_ids or oid in seen_occurrences:
            raise ValueError('Duplicate source-context review')
        seen_ids.add(identity)
        seen_occurrences.add(oid)
        date.fromisoformat(review['review_date'])
        occurrence = by_occurrence.get(oid)
        kind = review.get('kind', 'mercenary_narrative')
        fields = (
            (*OCCURRENCE_FIELDS, 'class')
            if kind
            in (
                'player_equipment',
                'variant_mercenary_narrative',
                'variant_player_narrative',
                'socket_component_reference',
                'qualified_named_prose',
                'player_pattern',
                'player_charm_pattern',
                'mercenary_equipment',
                'mercenary_prose_correction',
                'mercenary_table_correction',
                'mercenary_table_pattern_correction',
                'mercenary_support_reference',
                'player_prose_repeat',
                'player_pattern_prose_repeat',
                'player_utility_reference',
            )
            else OCCURRENCE_FIELDS
        )
        if (
            not isinstance(review.get('reason'), str)
            or not review['reason'].strip()
            or not occurrence
            or oid not in eligible
            or not identity_context_supported(kind, occurrence)
            or occurrence.get('variant') != 'Guide mention'
            or not occurrence_context_supported(kind, occurrence)
            or review.get('expected_occurrence') != {key: occurrence.get(key) for key in fields}
        ):
            raise ValueError('Changed or unsupported source-context occurrence')
        source = review['source']
        if source['path'] != 'pricing/data/appraisal-guide-sections.json' or occurrence_source(source) != (
            occurrence['source_id'],
            occurrence['source_locator'],
        ):
            raise ValueError('Source-context reference does not identify the exact span')
        span = reference(source)
        if (
            span != source.get('expected')
            or span.get('label') != occurrence['original_label']
            or any(span.get(key) != occurrence[key] for key in ('side', 'slot'))
        ):
            raise ValueError('Source-context span changed')
        evidence = review['evidence']
        guide_prefix = source['locator'].split('/item_spans/')[0] + '/'
        if (
            evidence['path'] != source['path']
            or not evidence['locator'].startswith(guide_prefix + 'sections/')
            or not isinstance(evidence.get('quote'), str)
            or not evidence['quote'].strip()
        ):
            raise ValueError('Source-context rationale needs a quote from the same guide')
        passage = reference(evidence)
        if (
            not isinstance(passage, str)
            or evidence['quote'] not in passage
            or occurrence['original_label'] not in evidence['quote']
        ):
            raise ValueError('Unsupported source-context quote')
        if kind in (
            'variant_mercenary_narrative',
            'variant_player_narrative',
            'player_prose_repeat',
            'player_pattern_prose_repeat',
            'player_utility_reference',
            'mercenary_support_reference',
            'socket_component_reference',
            'qualified_named_prose',
            'mercenary_table_correction',
            'mercenary_table_pattern_correction',
        ):
            guide = cache[(source['path'], source['sha256'])]['sources'][occurrence['source_id']]
            require_same_section(root, occurrence, guide, evidence, positions, label='source-context')
        if kind in ('mercenary_table_correction', 'mercenary_table_pattern_correction'):
            from pricing.knowledge.assessment.maintenance.mercenary_table_context import validate_table_context

            section_index = int(evidence['locator'].rsplit('/sections/', 1)[1].split('/')[0])
            validate_table_context(guide['sections'], section_index, review.get('wearer_quote', ''))
        branches = review.get('branches', [])
        if not branches or len({b['profile_id'] for b in branches}) != len(branches):
            raise ValueError('Missing or duplicate source-context configuration')
        for branch in branches:
            role = by_profile.get(branch['profile_id'])
            if (
                not role
                or role['id'] not in endorsed
                or branch.get('profile_fingerprint') != fingerprint(role)
                or not branch_identity_matches(kind, branch, role, occurrence, evidence['quote'], uses)
                or role.get('build') != occurrence['build']
                or role.get('side')
                != (
                    'merc'
                    if kind
                    in (
                        'mercenary_prose_correction',
                        'mercenary_support_reference',
                        'mercenary_table_correction',
                        'mercenary_table_pattern_correction',
                    )
                    else 'player'
                    if kind == 'qualified_named_prose'
                    else occurrence['side']
                )
                or any(role.get(key) != branch.get(key) for key in ('variant', 'slot'))
                or (
                    kind not in ('variant_player_narrative', 'variant_mercenary_narrative')
                    and (
                        role['source']['path'] != source['path']
                        or role['source']['sha256'] != source['sha256']
                        or not role['source']['locator'].startswith(guide_prefix)
                    )
                )
                or not branch_context_matches(kind, branch, role, occurrence, evidence['quote'])
            ):
                raise ValueError('Stale or incompatible source-context configuration')
            if kind in ('variant_player_narrative', 'variant_mercenary_narrative'):
                validate_variant_primary(role, occurrence, evidence['quote'], reference)
                validate_choices(branch, role, root)
            if kind == 'player_charm_pattern' and role['source']['locator'] != source['locator']:
                raise ValueError('source-context charm review must bind the exact primary span')
            if kind == 'qualified_named_prose':
                validate_named_primary(role, occurrence, reference(role['source']))
            if kind == 'socket_component_reference':
                validate_socket_entry(root, occurrence, guide, branch)
            if kind == 'player_utility_reference':
                validate_utility_primary(branch, role, reference(role['source']))
            if kind in ('player_prose_repeat', 'player_pattern_prose_repeat'):
                primary = reference(role['source'])
                if not isinstance(primary, dict) or any(
                    not span.get(key) or span[key] != primary.get(key) for key in ('profile_id', 'item_id')
                ):
                    raise ValueError('source-context prose must repeat the exact reviewed planner item')
        remaining = review.get('remaining_branches')
        if not isinstance(remaining, list) or any(
            not isinstance(value, str) or not value.strip() for value in remaining
        ):
            raise ValueError('Source-context branch review must be explicit')
        branch_ids = {branch['profile_id'] for branch in branches}
        remaining = list(
            dict.fromkeys(
                [
                    *remaining,
                    *(
                        gap
                        for use in uses
                        if use['profile_id'] in branch_ids
                        for gap in use.get('source_coverage', {}).get('remaining_branches', [])
                    ),
                ]
            )
        )
        if kind == 'mercenary_equipment':
            validate_mercenary_branches(review, remaining, evidence['quote'])
        result.append(
            {
                'id': identity,
                'occurrence_id': oid,
                'state': 'pending' if remaining else 'reviewed',
                'reason': review['reason'],
                'profile_ids': sorted(b['profile_id'] for b in branches),
                'remaining_branches': list(remaining),
                'source': {'artifact': 'source_context_reviews', 'locator': f'/rows/{index}'},
            }
        )
    return result
