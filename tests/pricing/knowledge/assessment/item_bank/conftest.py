"""Allow red/green against staged artifacts and final checks against publication."""

from tests.pricing.knowledge.assessment.item_bank.subset import default_ids, full_bank


def pytest_addoption(parser):
    parser.addoption(
        '--item-bank-staged',
        action='store_true',
        default=False,
        help='Run item-bank appraisal against rebuilt working-tree artifacts instead of publication.',
    )


def pytest_collection_modifyitems(config, items):
    """Default runs take the stratified subset (subset.py); D2R_ITEM_BANK=full or a named case runs all."""
    if full_bank():
        return
    named = {arg.split('::', 1)[1] for arg in config.args if '[' in arg and '::' in arg}
    keep, drop = [], []
    for item in items:
        case = getattr(item, 'callspec', None) and item.callspec.params.get('case')
        if (
            item.originalname != 'test_constructed_item_through_published_appraisal'
            or case is None
            or case.id in default_ids()
            or item.nodeid.split('::', 1)[1] in named
        ):
            keep.append(item)
        else:
            drop.append(item)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep
