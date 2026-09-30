"""Reviewed exact table links reuse rules without merging variant configurations."""

import hashlib
import json
from datetime import date
from pathlib import Path

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.charm_table_pattern import (
    KIND as CHARM_KIND,
    validate_pattern as validate_charm_pattern,
)
from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.player_table_context import TableMentions, require_player_table
from pricing.knowledge.assessment.maintenance.prose_socket_links import (
    KIND as PROSE_SOCKET_KIND,
    validate_link as validate_prose_socket,
)
from pricing.knowledge.assessment.maintenance.qualified_table_context import require_qualification
from pricing.knowledge.assessment.maintenance.resistance_armor_links import KIND as RESISTANCE_KIND, validate_link
from pricing.knowledge.assessment.maintenance.socketed_table_pattern import KINDS, validate_pattern
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq
from pricing.knowledge.assessment.maintenance.structured_main_tables import (
    KIND as MAIN_KIND,
    validate_link as validate_main,
)
from pricing.knowledge.assessment.maintenance.structured_named_variants import (
    KIND as NAMED_KIND,
    validate_link as validate_named,
)
from pricing.knowledge.assessment.maintenance.structured_variant_mirrors import KIND as MIRROR_KIND, validate_mirror
from pricing.knowledge.assessment.policies.sources import resolve_pointer
from pricing.knowledge.assessment.profile_sources import validate_profile_sources


def _read(root, pin):
    path = (root / pin['path']).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Missing table equivalence evidence')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError('Stale table equivalence evidence')
    return raw


def compile_table_equivalence(document, occurrences, profiles, uses, root):
    if document is None:
        return []
    if document.get('schema_version') != 1 or not isinstance(document.get('rows'), list):
        raise ValueError('Invalid table equivalence schema')
    compile_demand(uses, profiles)
    by_occurrence = {o['id']: o for o in occurrences}
    by_profile = {p['id']: p for p in profiles}
    seen, result = set(), []
    documents, decoded, guides = {}, {}, {}

    def read(pin):
        key = pin['path'], pin['sha256']
        if key not in documents:
            documents[key] = _read(root, pin)
        return documents[key]

    def read_json(pin):
        key = pin['path'], pin['sha256']
        if key not in decoded:
            decoded[key] = json.loads(read(pin))
        return decoded[key]

    for review in document['rows']:
        oid = review['occurrence_id']
        pattern = review.get('pattern_kind') in KINDS or review.get('pattern_kind') == CHARM_KIND
        if oid in seen:
            raise ValueError('Duplicate table equivalence review')
        seen.add(oid)
        date.fromisoformat(review['review_date'])
        for evidence in review.get('corroborating', []):
            read(evidence)
        occurrence, role = by_occurrence.get(oid), by_profile.get(review['profile_id'])
        if review.get('pattern_kind') == PROSE_SOCKET_KIND:
            equipment_id = review.get('equipment_occurrence_id')
            equipment_reviews = [r for r in document['rows'] if r['occurrence_id'] == equipment_id]
            if len(equipment_reviews) != 1:
                raise ValueError('Prose socket requires exactly one reviewed equipment link')
            result.append(
                validate_prose_socket(
                    review,
                    occurrence,
                    role,
                    equipment_reviews[0],
                    by_occurrence.get(equipment_id),
                    uses,
                    root,
                    read_json,
                )
            )
            continue
        if review.get('pattern_kind') == MAIN_KIND:
            result.append(validate_main(review, occurrence, role, uses, root, read, read_json))
            continue
        if review.get('pattern_kind') == NAMED_KIND:
            result.append(validate_named(review, occurrence, role, uses, root, read_json))
            continue
        if review.get('pattern_kind') == MIRROR_KIND:
            result.append(validate_mirror(review, occurrence, role, uses, root, read_json))
            continue
        if review.get('pattern_kind') == RESISTANCE_KIND:
            result.append(validate_link(review, occurrence, role, uses, root, read, read_json))
            continue
        if (
            not occurrence
            or not role
            or not isinstance(review.get('reason'), str)
            or not review['reason'].strip()
            or fingerprint(occurrence) != review['occurrence_fingerprint']
            or fingerprint(role) != review['profile_fingerprint']
            or (not pattern and occurrence.get('identity_status') != 'resolved')
            or occurrence.get('variant') != 'Guide mention'
            or role.get('variant') != 'Main alternatives'
            or role.get('review_status') != 'reviewed_candidate_rule'
            or occurrence.get('class') not in CLASS_NAMES
            or not requires_eq(role.get('must', {}), 'context_eq', 'player_class', occurrence['class'])
            or occurrence.get('side') != 'player'
            or role.get('side') != 'player'
            or any(role.get(key) != occurrence.get(key) for key in ('build', 'slot'))
            or (not pattern and role.get('names') != [occurrence.get('name')])
            or (
                occurrence.get('original_label') not in (occurrence.get('name'), review.get('qualified_label'))
                and not (
                    occurrence.get('name') in ('Deathbit', 'The Scalper')
                    and occurrence.get('original_label') == f'Ethereal {occurrence["name"]}'
                    and review.get('qualified_label') == f'Ethereal {occurrence["name"]} (Upgraded)'
                )
            )
        ):
            raise ValueError('Incompatible table equivalence context')
        endorsed = [
            u
            for u in uses
            if u['profile_id'] == role['id']
            and fingerprint(u) == review['use_fingerprint']
            and (
                (u.get('pattern') == role['id'] and u.get('pattern_label') == review.get('pattern_label'))
                if pattern
                else u.get('item') == occurrence['name']
            )
            and u.get('review_state') == 'reviewed'
            and u.get('scope') == 'softcore'
            and u.get('strength') in ('required', 'preferred', 'alternative')
            and not u.get('historical')
            and not u.get('source_coverage')
        ]
        if len(endorsed) != 1:
            raise ValueError('Table equivalence lacks an exact reviewed endorsement')
        source = role['source']
        try:
            validate_profile_sources({'profiles': [role]}, root, Path.read_bytes)
        except (ValueError, OSError) as error:
            raise ValueError('Table equivalence role evidence is stale or invalid') from error
        prefix = f'/{role["build"]}/slots/{role["slot"].replace("~", "~0").replace("/", "~1")}/'
        if source['path'] != 'pricing/data/wp-a-builds.json' or not source['locator'].startswith(prefix):
            raise ValueError('Table equivalence requires an exact primary slot entry')
        suffix = source['locator'][len(prefix) :]
        if not suffix.isdecimal() or str(int(suffix)) != suffix:
            raise ValueError('Table equivalence cannot reference a composite slot')
        primary = read_json(source)
        primary_label = resolve_pointer(primary, source['locator'])
        qualified = review.get('pattern_label') if pattern else review.get('qualified_label')
        if qualified is not None:
            if qualified != primary_label:
                raise ValueError('Table qualification differs from the primary label')
            if not pattern:
                require_qualification(role, qualified)
        try:
            if (
                primary_label != (qualified if qualified is not None else occurrence['name'])
                or primary[role['build']]['class'] != occurrence['class']
            ):
                raise ValueError('Table equivalence primary identity differs')
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError('Table equivalence primary entry is missing') from error
        guide = f'pricing/raw/mr/guides__{role["build"]}.html'
        if review['guide']['path'] != guide or occurrence['source_id'] != guide:
            raise ValueError('Table equivalence belongs to another guide')
        if review['cache']['path'] != 'pricing/data/appraisal-guide-sections.json':
            raise ValueError('Table equivalence requires the guide extraction cache')
        cache = read_json(review['cache'])['sources'][guide]
        guide_key = guide, review['guide']['sha256'], review['cache']['sha256']
        if guide_key not in guides:
            html = read(review['guide']).decode()
            parser = TableMentions()
            parser.feed(html)
            parser.close()
            sections = section_inventory(html)['sections']
            if parser.mentions != cache['item_spans'] or sections != cache['sections']:
                raise ValueError('Table equivalence raw guide and cache differ')
            guides[guide_key] = parser, sections
        parser, sections = guides[guide_key]
        locator = occurrence['source_locator']
        if not locator.startswith('/item-spans/') or not locator.removeprefix('/item-spans/').isdecimal():
            raise ValueError('Table equivalence requires an exact span')
        index = int(locator.removeprefix('/item-spans/'))
        if index >= len(parser.mentions):
            raise ValueError('Table equivalence span is missing')
        require_player_table(parser, sections, index)
        if pattern:
            validator = validate_charm_pattern if review.get('pattern_kind') == CHARM_KIND else validate_pattern
            validator(review, role, occurrence, parser, index, read_json)
        if qualified is not None and not pattern and parser.entry_labels[index] != qualified:
            raise ValueError('Table qualification differs from the complete HTML entry')
        span = parser.mentions[index]
        if (
            span['label'] != occurrence['original_label']
            or any(span[k] != occurrence[k] for k in ('side', 'slot'))
            or span['slot'] == 'unspecified'
        ):
            raise ValueError('Table equivalence span has another identity or context')
        result.append(
            {
                'occurrence_id': oid,
                'profile_id': role['id'],
                'state': 'reviewed',
                'reason': review['reason'],
                'review_date': review['review_date'],
            }
        )
    return result
