"""Replay saved captures through the current decoder, offline KB and shared report.

Run with python -m pricing.knowledge.assessment.maintenance.replay. Snapshot
fixtures retain historical evidence; a successful replay is not a live probe.
"""

import argparse
import json
from pathlib import Path

from inventory_tracking.appraisal.text import format_appraisal
from inventory_tracking.items.decode import decode_items
from inventory_tracking.items.modifiers import owned_damage_modifiers, owned_defense_modifiers
from pricing.knowledge.__main__ import DEFAULT_DATABASE
from pricing.knowledge.pipeline import retrieve_draft


ROOT = Path(__file__).resolve().parents[4]
STEMS = (
    'sazabi_mental_sheath',
    'dread_edge',
    'cryptic_axe',
    'superior_phase_blade',
    'spirit_monarch',
    'insight_bill',
    'guardian_angel',
    'storm_gyre',
    'greater_claws',
    'dire_song',
    'authority_mage_plate',
    'tancred_crowbill',
    'harlequin_crest',
    'atma_scarab',
    'large_charm_life20',
    'large_charm_life35',
    'hellplague',
    'runic_talons',
)


def replay(stem, database=DEFAULT_DATABASE):
    if stem not in STEMS:
        raise ValueError(f'Unknown saved-item replay: {stem}')
    path = ROOT / 'tests/pricing/knowledge/assessment/fixtures/replays' / f'{stem}.json'
    if not path.exists():
        path = ROOT / 'tests/inventory_tracking/fixtures' / f'{stem}.json'
    saved = json.loads(path.read_text())
    row = saved['snapshot']['resources']['items'][0]
    arrays = row['resource_stats']
    if arrays.get('stat_diagnostics') and 'stats_pointer' in row:
        arrays['damage_modifiers'] = owned_damage_modifiers(arrays['stat_diagnostics'], row)
        arrays['defense_modifiers'] = owned_defense_modifiers(arrays['stat_diagnostics'], row)
    extraction = decode_items(
        saved['snapshot'],
        saved['report'],
        inventory_page=row['details']['inventory_page'],
        inventory_owner_id=row['details']['owner_id'],
    )[0]
    result = retrieve_draft(extraction, database)
    return {
        'source': str(path.relative_to(ROOT)),
        'extraction': extraction,
        'assessment': result['assessment'],
        'price_estimate': result['price_estimate'],
        'text': format_appraisal({'state': 'complete', 'request_id': stem, 'result': result}),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('items', nargs='*', choices=STEMS)
    parser.add_argument('--publication-store', type=Path, help='Replay decoding and retrieval in one published KB')
    args = parser.parse_args()
    if args.publication_store:
        from pricing.knowledge.publication_repository import PublicationRepository
        from pricing.knowledge.published_runtime import published_snapshot

        loaded = PublicationRepository(args.publication_store).load()
        if loaded.runtime is None:
            raise ValueError('; '.join(loaded.issues))
        with published_snapshot(loaded.runtime):
            print(
                json.dumps(
                    {stem: replay(stem, database=loaded.runtime.database) for stem in args.items or STEMS}, indent=2
                )
            )
        return
    print(json.dumps({stem: replay(stem) for stem in args.items or STEMS}, indent=2))


if __name__ == '__main__':
    main()
