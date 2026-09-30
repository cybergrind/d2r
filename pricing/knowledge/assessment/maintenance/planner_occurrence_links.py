"""Link exact planner equipment and rune children to validated full-payload reviews."""

import hashlib
import json
from datetime import date

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.builds import decode_planner


TABLE = 'pricing/knowledge/assessment/rules/table_equivalence_reviews.json'
NATIVE = 'third-parties/d2data/json/misc.json'
COVERAGES = {'player_rune_socket_component', 'player_runeword_component', 'merc_runeword_component'}


def indexed(rows, key='id'):
    result = {r[key]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Planner link duplicate inventory or review')
    return result


def compile_planner_occurrence_links(document, table, dispositions, inventory, root):
    if document is None:
        return []

    def resolve(link, read):
        if read(TABLE) != table:
            raise ValueError('Planner link endorsement artifact changed')
        reviews = indexed(table['rows'], 'occurrence_id')
        proofs = indexed(dispositions, 'occurrence_id')
        endorsement = reviews.get(link['endorsement_occurrence_id'], {})
        proof = proofs.get(link['endorsement_occurrence_id'], {})
        evidence = endorsement.get('planner_endorsement', {})
        if (
            fingerprint(endorsement) != link['endorsement_sha256']
            or proof.get('state') != 'reviewed'
            or not endorsement.get('profile_id')
            or proof.get('profile_id') != endorsement['profile_id']
            or evidence.get('coverage') not in COVERAGES
        ):
            raise ValueError('Planner link requires a validated complete rune-payload endorsement')
        return endorsement, evidence

    return compile_validated_planner_links(document, inventory, root, resolve)


def compile_validated_planner_links(document, inventory, root, resolve):
    if document is None:
        return []
    if document.get('schema_version') != 1:
        raise ValueError('Planner link schema changed')
    inputs, cache = document['inputs'], {}

    def read(name):
        if name not in cache:
            path = (root / name).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError('Planner link source missing or unsafe')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != inputs.get(name):
                raise ValueError('Planner link source stale or unpinned')
            cache[name] = json.loads(raw)
        return cache[name]

    native = read(NATIVE)
    occurrences = indexed(inventory['occurrences'])
    identities = indexed(inventory['identities'])
    sources = indexed(inventory['sources'])
    seen, result = set(), []
    for link in document['rows']:
        endorsement, evidence = resolve(link, read)
        date.fromisoformat(link['reviewed_at'])
        if not link.get('reason', '').strip():
            raise ValueError('Planner link requires a review reason')
        pin = evidence['planner']
        name = pin['path']
        source = sources.get(name, {})
        if (
            inputs.get(name) != pin['sha256']
            or source.get('sha256') != pin['sha256']
            or source.get('actual_sha256') != pin['sha256']
            or source.get('status') != 'verified'
            or source.get('path') != name
        ):
            raise ValueError('Planner link source binding changed')
        planner = decode_planner(read(name))
        side = 'merc' if evidence['coverage'].startswith('merc_') else 'player'
        container = 'mercItems' if side == 'merc' else 'items'
        index, slot = evidence['profile_index'], evidence['slot']
        try:
            profile = planner['profiles'][index]
            item_id = str(profile[container][slot])
            item = planner['items'][item_id]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError('Planner link equipment missing') from error
        if (
            item_id != evidence['item_id']
            or item != evidence['expected_item']
            or profile.get('uid') != evidence.get('profile_uid')
            or profile.get('name') != evidence['profile_name']
        ):
            raise ValueError('Planner link equipment or variant changed')
        codes = item.get('socketedItems', [])
        if not codes or len(codes) != item.get('sockets') or len(link['children']) != len(codes):
            raise ValueError('Planner link must include the complete rune payload')
        parent_locator = f'/profiles/{index}/{container}/{slot}'

        def occurrence(ref, locator, *, name=name, profile=profile, side=side, slot=slot):
            row = occurrences.get(ref['occurrence_id'], {})
            identity = identities.get(row.get('identity_id'), {})
            if (
                not row
                or row['id'] in seen
                or fingerprint(row) != ref['sha256']
                or row.get('source_id') != name
                or row.get('source_locator') != locator
                or row.get('kind') != 'demand'
                or row.get('source_status') != 'verified'
                or row.get('identity_status') != 'resolved'
                or row.get('variant') != profile['name']
                or row.get('side') != side
                or row.get('slot') != slot
                or identity.get('name') != row.get('name')
                or identity.get('category') != row.get('category')
            ):
                raise ValueError('Planner link occurrence identity, payload slot or context changed')
            seen.add(row['id'])
            return row

        parent = occurrence(link['parent'], parent_locator)
        if (
            parent.get('name') != endorsement['canonical_name']
            or parent.get('base_code') != item.get('base')
            or any(parent.get('details', {}).get(k) != v for k, v in item.items())
            or parent.get('details', {}).get('container') != container
        ):
            raise ValueError('Planner link parent differs from endorsed equipment')
        linked = [parent]
        for position, (code, ref) in enumerate(zip(codes, link['children'], strict=True)):
            definition = native.get(code, {}) if isinstance(code, str) else {}
            child = occurrence(ref, f'{parent_locator}/socketedItems/{position}')
            if (
                definition.get('type') != 'rune'
                or definition.get('code') != code
                or child.get('name') != definition.get('name')
                or child.get('original_label') != definition.get('name')
                or child.get('category') != 'misc'
                or child.get('base_code') != code
                or any(
                    child.get('details', {}).get(k) != v
                    for k, v in {
                        'base': code,
                        'canonical_id': code,
                        'container': 'socketedItems',
                        'role': 'socket_filler',
                    }.items()
                )
            ):
                raise ValueError('Planner link child differs from native rune payload')
            linked.append(child)
        for row in linked:
            result.append(
                {
                    'occurrence_id': row['id'],
                    'identity_id': row['identity_id'],
                    'state': 'reviewed',
                    'profile_id': endorsement['profile_id'],
                    'parent_occurrence_id': parent['id'],
                    'endorsement_occurrence_id': endorsement['occurrence_id'],
                    'source_id': name,
                    'source_locator': row['source_locator'],
                    'source_sha256': pin['sha256'],
                    'reviewed_at': link['reviewed_at'],
                    'reason': link['reason'],
                }
            )
    return result
