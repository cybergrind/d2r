"""Exact source reviews for Cube storage and recipe prose, independent of gear demand."""

import hashlib
import json
import re
from datetime import date

from pricing.knowledge.assessment.maintenance.carried_cube_reviews import occurrence_fingerprint
from pricing.knowledge.assessment.maintenance.guide_positions import PositionedMentions
from pricing.knowledge.assessment.maintenance.guide_sections import SectionParser


CACHE = 'pricing/data/appraisal-guide-sections.json'
MARKER = '@CUBE@'


class MarkedSectionParser(SectionParser):
    def __init__(self, position):
        super().__init__()
        self.position = position

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        if self.getpos() == self.position:
            self.handle_data(MARKER)


def marked_sections(html, guide, span_index):
    """Retain extractor semantics, inserting a marker only at the selected source span."""
    if MARKER in html:
        raise ValueError('Cube marker already present in source')
    parser = PositionedMentions()
    parser.feed(html)
    parser.close()
    if parser.mentions != guide['item_spans'] or not 0 <= span_index < len(parser.positions):
        raise ValueError('Cube source spans changed')
    marked = MarkedSectionParser(parser.positions[span_index])
    marked.feed(html)
    marked.close()
    texts = [' '.join(''.join(s['parts']).split()) for s in marked.sections]
    if [t.replace(MARKER, '') for t in texts] != [s['text'] for s in guide['sections']]:
        raise ValueError('Cube source sections changed')
    return texts


def _classification(quote):
    """Small reviewed utility templates; these never assert gear fit or recipe validity."""
    if quote.count(MARKER + 'Horadric Cube') != 1 or quote.count('Horadric Cube') != 1:
        return None
    if re.fullmatch(
        r'(?:Repair|Recharge) (?:this Wand|it) .+Chipped Gem \+ Ort Rune '
        r'@CUBE@Horadric Cube [Rr]ecipe(?: to regain the Charges)?\.',
        quote,
    ):
        return 'recharge_recipe_context'
    if quote == 'Upgrade your Boots to the highest base possible, using the @CUBE@Horadric Cube recipe.':
        return 'upgrade_recipe_context'
    storage = (
        'Keep a Lower Resist Charge Wand in your inventory and/or @CUBE@Horadric Cube '
        'to break monster Fire Immunity/lower monster Fire Resistances if necessary.',
        "Keep a back-up Titan's Revenge or Thunderstroke in your inventory "
        '(inside the @CUBE@Horadric Cube to save space) to swap to when Quantity is depleted on your active weapon.',
        'Keep additional Javelin in your inventory or @CUBE@Horadric Cube to minimize repair trip frequency.',
        'Before obtaining Flame Rift and/or Infinity, you should purchase a Lower Resist Charge Wand '
        'from Nightmare Drognan and either equip it on your Weapon-Swap '
        'or keep it in your inventory/@CUBE@Horadric Cube.',
        'Utilize your @CUBE@Horadric Cube to put Arachnid Mesh, Magefist, and a Faster Cast Rate Ring into it.',
        'Switch to Memory from your @CUBE@Horadric Cube and buff yourself with Frozen Armor and Energy Shield as well.',
    )
    return 'storage_context' if quote in storage else None


def compile_cube_narrative_reviews(document, inventory, root):
    if document is None:
        return []
    if document.get('schema_version') != 1 or document.get('scope') != 'horadric_cube_narrative_only':
        raise ValueError('Unsupported Cube narrative scope')

    def index(rows):
        indexed = {r['id']: r for r in rows}
        if len(indexed) != len(rows):
            raise ValueError('Duplicate Cube narrative source or identity')
        return indexed

    occurrences = index(inventory['occurrences'])
    identities = index(inventory['identities'])
    sources = index(inventory.get('sources', []))
    inputs, loaded = document['inputs'], {}

    def source(name):
        if name not in loaded:
            path = (root / name).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError('Missing or unsafe Cube narrative source')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != inputs.get(name):
                raise ValueError('Stale or unpinned Cube narrative source')
            loaded[name] = raw.decode()
        return loaded[name]

    cache = json.loads(source(CACHE))['sources']
    result, seen = [], set()
    for review in document['rows']:
        oid = review['occurrence_id']
        if oid in seen or oid not in occurrences:
            raise ValueError('Duplicate or missing Cube narrative occurrence')
        seen.add(oid)
        row = occurrences[oid]
        date.fromisoformat(review['reviewed_at'])
        if occurrence_fingerprint(row) != review['occurrence_sha256'] or not review.get('reason', '').strip():
            raise ValueError('Changed or unexplained Cube narrative review')
        expected = {
            'name': 'Horadric Cube',
            'original_label': 'Horadric Cube',
            'kind': 'demand',
            'category': 'misc',
            'variant': 'Guide mention',
            'side': 'player',
            'slot': 'unspecified',
            'identity_status': 'resolved',
            'source_status': 'verified',
        }
        identity = identities.get(row.get('identity_id'), {})
        if (
            any(row.get(k) != v for k, v in expected.items())
            or row.get('details', {}).get('role') != 'guide_mention'
            or identity.get('name') != 'Horadric Cube'
            or identity.get('category') != 'misc'
        ):
            raise ValueError('Unsupported Cube narrative identity or context')
        name = row['source_id']
        match = re.fullmatch(r'/item-spans/(0|[1-9]\d*)', row['source_locator'])
        binding = sources.get(name, {})
        if (
            not re.fullmatch(r'pricing/raw/mr/guides__[^/]+\.html', name)
            or match is None
            or binding.get('path') != name
            or binding.get('status') != 'verified'
            or not inputs.get(name)
            or binding.get('sha256') != inputs[name]
            or binding.get('actual_sha256') != inputs[name]
        ):
            raise ValueError('Cube narrative source binding changed')
        guide = cache.get(name, {})
        if guide.get('source_sha256') != inputs[name]:
            raise ValueError('Cube narrative cached source changed')
        texts = marked_sections(source(name), guide, int(match[1]))
        section, quote = review['section_index'], review['quote']
        if (
            type(section) is not int
            or not 0 <= section < len(texts)
            or not quote
            or quote not in texts[section]
            or _classification(quote) != review.get('classification')
            or review.get('classification') is None
        ):
            raise ValueError('Cube narrative quote or classification does not bind this span')
        result.append(
            {
                'occurrence_id': oid,
                'identity_id': row['identity_id'],
                'state': 'reviewed',
                'classification': review['classification'],
                'reason': review['reason'],
                'reviewed_at': review['reviewed_at'],
                'source_id': name,
                'source_locator': row['source_locator'],
                'source_sha256': inputs[name],
                'section_index': section,
                'quote': quote.replace(MARKER, ''),
            }
        )
    return result
