"""Replay the corpus through the offline assessment and compare verdicts with the user's labels.

    uv run --offline python -m inventory_tracking.corpus.score [--all] [--save baseline]

Without labels (or with --all) it prints the verdict distribution of every corpus item.

Each item is judged by the one assessment entry point at CORPUS (loot/assess.py; design.md §10.4 step 2, 2026-10-23):
the detail engine's result is its price source, the identify verdict (loot/assess.py `identify_verdict`, the one the
live BOOK holds) the verdict scored, and the outcome the town would give it as the loop's (keep / vendor, `card_score`)
beside it. The verdicts equal identify/service.py `verdict_for`'s on every corpus item (2026-10-23, the gate:
rca/2026-10-23/scripts/assess_2b_corpus.py).
"""

import argparse
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from inventory_tracking.corpus.build import DATA
from inventory_tracking.loot.assess import GIVE_UP, Assessment, Assessor, ResultAppraiser, Site
from inventory_tracking.loot.facts import Owner, Where, from_observation


if TYPE_CHECKING:
    from inventory_tracking.appraisal.published_backend import Loaded


WORTH = frozenset({'sell', 'slow'})  # labels the player wants flagged as trade value
_LOADED: Loaded | None = None  # the publication a pool worker holds, set by `_init`


def load(data: Path):
    items = [json.loads(line) for line in (data / 'items.jsonl').read_text().splitlines()]
    labels_path = data / 'labels.json'
    labels = json.loads(labels_path.read_text()) if labels_path.exists() else {}
    return items, labels


def _init(store):
    from inventory_tracking.appraisal.published_backend import process_publications
    from pricing.api import pointer_generation

    global _LOADED
    _LOADED = process_publications(store).get(pointer_generation(store), validate=False)


def corpus_assessment(observation, result) -> Assessment:
    """A recorded read judged at CORPUS by the one entry point: `result` the detail engine's, its verdict the
    identify worker's (`ResultAppraiser`'s default), no owned copies told (S8), no live state."""
    facts = from_observation(observation, where=Where.INVENTORY, owner=Owner.LOOP)
    return Assessor(ResultAppraiser(lambda _: result)).assess(facts, Site.CORPUS)


def _assess(row) -> dict[str, Any]:
    from pricing.api import published_snapshot, retrieve_draft

    judged: dict[str, Any] = {}
    try:
        loaded = _LOADED
        if loaded is None:
            raise ValueError('No publication loaded in this worker')
        with published_snapshot(loaded.runtime):
            result = retrieve_draft(row['observation'], loaded.runtime.database, as_of=datetime.now(UTC).date())
        assessment = corpus_assessment(row['observation'], result)
        if assessment.value is None or assessment.value.verdict is None:
            raise ValueError(f'no appraisal: {assessment.why}')
        verdict, reason = assessment.value.verdict, assessment.value.reason or assessment.why
        estimate = (result.get('price_estimate') or {}).get('estimate_ist')
        judged = {'outcome': assessment.outcome.value, 'rule': assessment.rule, 'why': assessment.why}
    except Exception as exc:
        verdict, reason, estimate = 'error', str(exc)[:120], None
    item = row['observation']['item']
    return {
        'id': row['id'],
        'name': item.get('name'),
        'rarity': item.get('rarity'),
        'verdict': verdict,
        'reason': reason,
        'estimate_ist': estimate,
        **judged,
    }


def assess_all(rows, store, workers=6):
    with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(store,)) as pool:
        return list(pool.map(_assess, rows, chunksize=4))


def score(results, labels, *, legacy=False) -> dict:
    """Measure trade recall and liquid SELL precision; keep the old baseline explicit."""
    labelled = [(labels[r['id']], r) for r in results if r['id'] in labels]
    worth = [r for label, r in labelled if label in WORTH]
    flagged = {'keep'} if legacy else WORTH
    positive = WORTH if legacy else {'sell'}
    keeps = [(label, r) for label, r in labelled if r['verdict'] == ('keep' if legacy else 'sell')]
    sell_labelled = [r for label, r in labelled if label == 'sell']

    def priced(row):
        return (row.get('estimate_ist') if legacy else (row.get('band') or {}).get('median_ist')) is not None

    return {
        'mode': 'legacy' if legacy else 'triage',
        'labelled': len(labelled),
        'worth': len(worth),
        'checks': sum(r['verdict'] == 'check' for r in results),
        'check_recall': round(
            sum(r['verdict'] == 'check' for label, r in labelled if label == 'check')
            / sum(label == 'check' for label, _ in labelled),
            3,
        )
        if any(label == 'check' for label, _ in labelled)
        else None,
        'recall': round(sum(r['verdict'] in flagged for r in worth) / len(worth), 3) if worth else None,
        'keeps': len(keeps),
        'precision': round(sum(label in positive for label, _ in keeps) / len(keeps), 3) if keeps else None,
        'priced': sum(priced(r) for _, r in labelled),
        'sell_band_coverage': round(sum(priced(r) for r in sell_labelled) / len(sell_labelled), 3)
        if sell_labelled
        else None,
        'confusion': {
            f'{label}→{verdict}': count
            for (label, verdict), count in sorted(Counter((label, r['verdict']) for label, r in labelled).items())
        },
        'missed': [f'{r["name"]} ({r["rarity"]}): {r["reason"]}' for r in worth if r['verdict'] not in flagged],
        'false_keeps': [f'{r["name"]} ({r["rarity"]}): {r["reason"]}' for label, r in keeps if label not in positive],
    }


def card_score(results, labels) -> dict[str, Any]:
    """The entry point's outcome against the labels: how many trade-value items (WORTH) it would vendor, and the
    outcome per label (keep / vendor / identify; the words of loot/assess.py `Outcome`)."""
    labelled = [(labels[r['id']], r) for r in results if r['id'] in labels and 'outcome' in r]
    worth = [r for label, r in labelled if label in WORTH]
    given_up = {outcome.value for outcome in GIVE_UP}
    return {
        'judged': sum('outcome' in r for r in results),
        'outcomes': dict(sorted(Counter(r['outcome'] for r in results if 'outcome' in r).items())),
        'worth_vendored': [
            f'{r["name"]} ({r["rarity"]}): {r["rule"]} {r["why"]}' for r in worth if r['outcome'] in given_up
        ],
        'confusion': {
            f'{label}→{outcome}': count
            for (label, outcome), count in sorted(Counter((label, r['outcome']) for label, r in labelled).items())
        },
    }


def main(argv=None):
    from pricing.api import DEFAULT_STORE

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=DATA)
    parser.add_argument('--all', action='store_true', help='assess every corpus item, not only labelled ones')
    parser.add_argument('--save', help='write the results to data/score-<name>.json')
    parser.add_argument('--results', type=Path, help='Score saved triage results without running the detail engine')
    parser.add_argument('--legacy', action='store_true', help='Interpret saved results as the old KEEP/CHECK verdicts')
    args = parser.parse_args(argv)
    items, labels = load(args.data)
    rows = items if args.all or not labels else [row for row in items if row['id'] in labels]
    if args.results:
        saved = json.loads(args.results.read_text())
        results = saved['results'] if isinstance(saved, dict) else saved
    else:
        results = assess_all(rows, DEFAULT_STORE)
    legacy = args.legacy or args.results is None
    by_rarity = Counter((r['rarity'], r['verdict']) for r in results)
    priced = sum(
        (r.get('estimate_ist') if legacy else (r.get('band') or {}).get('median_ist')) is not None for r in results
    )
    print(f'{len(results)} items assessed; {priced} with a price')
    for rarity in sorted({key[0] or '?' for key in by_rarity}):
        print(f'  {rarity:9s}', {v: n for (r, v), n in sorted(by_rarity.items(), key=str) if (r or '?') == rarity})
    summary = score(results, labels, legacy=legacy)
    if summary:
        print(json.dumps({k: v for k, v in summary.items() if k not in ('missed', 'false_keeps')}, indent=1))
        for key in ('missed', 'false_keeps'):
            print(f'{key} ({len(summary[key])}):')
            for line in summary[key]:
                print('  ' + line)
    if any('outcome' in r for r in results):
        print('entry point (CORPUS):', json.dumps(card_score(results, labels), indent=1))
    if args.save:
        output = args.data / f'score-{args.save}.json'
        output.write_text(json.dumps({'summary': summary, 'results': results}, indent=1) + '\n')
        print(f'saved {output}')


if __name__ == '__main__':
    main()
