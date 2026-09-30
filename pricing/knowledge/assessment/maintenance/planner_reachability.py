"""Conservative source reachability diagnostics; never an item-value disposition."""

from collections import defaultdict
from html.parser import HTMLParser

from pricing.knowledge.builds import decode_planner


CONTAINERS = {'items', 'mercItems', 'inventory', 'cube'}
PROFILE_METADATA = {
    'name',
    'skills',
    'stats',
    'class',
    'level',
    'active',
    'mercLevel',
    'difficulty',
    'weaponSet',
    'quests',
    'merc',
    'skillPos',
    'skillProgression',
    'buildinfo',
    'monster',
    'uid',
    'primarySkills',
    'mercName',
}
ROOT_METADATA = {
    'activeProfile',
    'buffs',
    'summons',
    'active',
    'class',
    'user',
    'name',
    'pinnedStats',
    'folder',
    'author',
}


def _empty_notes(notes):
    if not notes:
        return True
    paragraph = {
        'children': [],
        'direction': None,
        'format': '',
        'indent': 0,
        'type': 'paragraph',
        'version': 1,
    }
    return notes == {'root': {**paragraph, 'type': 'root', 'children': [paragraph]}}


class _References(HTMLParser):
    def __init__(self, catalog_ids):
        super().__init__()
        self.references = defaultdict(set)
        self.issues = []
        self.catalog_ids = catalog_ids
        self.catalog_references = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        # New tooltips often have no visible label and can point at definitions
        # outside the selected set's inventory. They still establish reachability.
        if 'data-d2-item-id' in values:
            embedded = (values.get('data-d2-item-id') or '').strip()
            planner = (values.get('data-d2-id') or '').strip()
            if not embedded:
                self.issues.append({'kind': 'missing_item', 'planner': planner, 'position': self.getpos()})
            elif not planner:
                self.issues.append({'kind': 'missing_planner', 'item': embedded, 'position': self.getpos()})
            else:
                self.references[planner].add(embedded)
        # Inspect both formats when present; neither is evidence to discard the other.
        item = values.get('data-d2planner-id')
        if item is None:
            return
        planner = values.get('data-d2planner-profile')
        if not planner and item.split('#', 1)[0] in self.catalog_ids:
            self.catalog_references.add(item)
        elif not planner:
            self.issues.append({'kind': 'missing_planner', 'item': item, 'position': self.getpos()})
        else:
            self.references[planner].add(item)


def guide_references(html, *, catalog_ids=()):
    """Read item links from every HTML element, regardless of guide ownership."""
    parser = _References(set(catalog_ids))
    parser.feed(html)
    parser.close()
    return {
        'references': {key: sorted(value) for key, value in sorted(parser.references.items())},
        'issues': parser.issues,
        'catalog_references': sorted(parser.catalog_references),
    }


def planner_reachability(document, guide_roots):
    """Find definition candidates only when the inspected structure is understood.

    Candidates still require source review. In particular, an unused definition
    says nothing about whether that item is useful or valuable elsewhere.
    """
    planner = decode_planner(document)
    definitions = planner['items']
    issues, reachable = [], set()
    unknown = set(planner) - ROOT_METADATA - {'items', 'profiles', 'notes'}
    if unknown:
        issues.append({'kind': 'unknown_root_fields', 'fields': sorted(unknown)})
    if not _empty_notes(planner.get('notes')):
        issues.append({'kind': 'notes_require_review'})

    def walk(ref, path, ancestors=(), *, mark=True):
        if ref is None:
            return
        if not isinstance(ref, (str, int, dict)) or isinstance(ref, bool):
            issues.append({'kind': 'unsupported_reference', 'path': path})
            return
        key = str(ref) if not isinstance(ref, dict) else None
        if key is not None and key in ancestors:
            issues.append({'kind': 'cycle', 'path': path, 'item': key})
            return
        item = ref if key is None else definitions.get(key)
        if item is None:
            # Direct base/rune codes are legal. Numeric refs must resolve.
            if key.isdecimal():
                issues.append({'kind': 'missing_definition', 'path': path, 'item': key})
            return
        if not isinstance(item, dict):
            issues.append({'kind': 'unsupported_definition', 'path': path})
            return
        if mark and key is not None:
            reachable.add(key)
        children = item.get('socketedItems', [])
        if not isinstance(children, list):
            issues.append({'kind': 'unsupported_socket_container', 'path': path})
            return
        parents = ancestors + ((key,) if key is not None else ())
        for number, child in enumerate(children):
            walk(child, f'{path}/socketedItems/{number}', parents, mark=mark)

    for number, profile in enumerate(planner['profiles']):
        if not isinstance(profile, dict):
            issues.append({'kind': 'unsupported_profile', 'profile': number})
            continue
        unknown = set(profile) - PROFILE_METADATA - CONTAINERS
        if unknown:
            issues.append({'kind': 'unknown_profile_fields', 'profile': number, 'fields': sorted(unknown)})
        for name in sorted(CONTAINERS):
            value = profile.get(name, {})
            if not isinstance(value, (dict, list)):
                issues.append({'kind': 'unsupported_container', 'profile': number, 'container': name})
                continue
            for slot, ref in value.items() if isinstance(value, dict) else enumerate(value):
                walk(ref, f'/profiles/{number}/{name}/{slot}')
    # The source audit collects these in a set. Stable traversal keeps issue
    # indices and completion-task records reproducible across Python processes.
    for ref in sorted(guide_roots, key=str):
        walk(ref, f'/guide/{ref}')

    def inspect_metadata(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f'{path}/{key}'
                if key in CONTAINERS or key == 'socketedItems':
                    issues.append({'kind': 'additional_equipment_context', 'path': child_path})
                    if isinstance(child, (dict, list)):
                        for slot, ref in child.items() if isinstance(child, dict) else enumerate(child):
                            walk(ref, f'{child_path}/{slot}')
                else:
                    inspect_metadata(child, child_path)
        elif isinstance(value, list):
            for number, child in enumerate(value):
                inspect_metadata(child, f'{path}/{number}')

    for field in sorted(ROOT_METADATA):
        inspect_metadata(planner.get(field), f'/{field}')
    for number, profile in enumerate(planner['profiles']):
        if isinstance(profile, dict):
            for field in sorted(PROFILE_METADATA):
                inspect_metadata(profile.get(field), f'/profiles/{number}/{field}')
    # Audit dormant definitions too: a broken graph is not proven unused data.
    for key in sorted(definitions):
        walk(key, f'/items/{key}', mark=False)
    return {
        'reachable': sorted(reachable),
        'unreachable_candidates': sorted(set(definitions) - reachable) if not issues else [],
        'issues': issues,
    }
