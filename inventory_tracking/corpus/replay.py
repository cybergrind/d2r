"""Triage score reports over the corpus, without detail-engine appraisal.

    uv run --offline python -m inventory_tracking.corpus.replay           # score-guides/-triage/-listings.json
    uv run --offline python -m inventory_tracking.corpus.replay --guides  # score-guides.json alone

The reports are pricing's (`pricing.triage.replay`, `pricing.triage.guide_cases`); the corpus and
the exact-verdict scorer are this package's, passed in.
"""

import argparse

from inventory_tracking.corpus.build import DATA, RUNS, merge
from inventory_tracking.corpus.score import load, score
from pricing.api import guide_report, triage_report


def read_corpus():
    merge(RUNS, DATA)
    return load(DATA)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--guides', action='store_true', help='extract and score the guide cases only')
    args = parser.parse_args(argv)
    if args.guides:
        guide_report(DATA, score)
    else:
        triage_report(DATA, read_corpus, score)


if __name__ == '__main__':
    main()
