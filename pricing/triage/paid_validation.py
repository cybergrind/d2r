"""Seller-held-out paid-property diagnostics; never changes live verdicts."""

from pricing.triage.paid_properties import compile_scores, lookup, split_sellers
from pricing.triage.replay import listing_score


def validate(rows, corpus, verdicts, property_ids, tables, *, negatives=()):
    common = (rows, corpus, verdicts, property_ids, tables['rules']['keep_ist'])
    full = compile_scores(*common, negatives=negatives, held_sellers=set())
    folds, membership = [], {}
    for fold in range(3):
        _, held = split_sellers(rows, fold)
        sellers = {str(row['seller_id']) for row in held}
        membership.update(dict.fromkeys(sellers, fold))
        folds.append(compile_scores(*common, negatives=negatives, held_sellers=sellers))

    def held_lookup(row, item):
        fold = membership.get(str(row.get('seller_id')))
        return lookup(item, folds[fold]['models']) if fold is not None else None

    def summarized(report):
        return {key: report[key] for key in ('overall', 'categories')}

    def models(report):
        rows = report['models']
        kept = sum(row['threshold'] <= len(row['properties']) for row in rows)
        return {'fitted': len(rows), 'deployable': kept, 'vetoed_or_over_threshold': len(rows) - kept}

    held = summarized(listing_score(rows, tables, diagnostic_scorer=held_lookup))
    in_sample = summarized(
        listing_score(rows, tables, diagnostic_scorer=lambda row, item: lookup(item, full['models']))
    )
    added = sum(held['categories'].get(category, {}).get('scorer_added_valuable', 0) for category in ('rare', 'magic'))
    return {
        'live_scorer_enabled': False,
        'method': 'three disjoint seller folds, trained on two and evaluated on the third',
        'in_sample': in_sample,
        'out_of_sample': held,
        'models': {'all_sellers': models(full), 'folds': [models(fold) for fold in folds]},
        'rare_magic_added_votes': added,
        'decision': 'remove' if added < 200 else 'eligible_for_further_validation',
    }
