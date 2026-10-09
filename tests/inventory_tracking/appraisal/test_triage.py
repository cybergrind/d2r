from inventory_tracking.appraisal.triage import headline


def test_headline_says_when_an_ethereal_copy_was_priced_as_the_normal_one():
    triage = {
        'verdict': 'check',
        'reason': 'no cached price evidence; name band is reference only',
        'decision_ist': None,
        'band': None,
        'ethereal_basis': 'priced as non-ethereal: gloves have no mercenary slot',
    }
    assert headline(triage).endswith(' · priced as non-ethereal: gloves have no mercenary slot')
    assert 'priced as non-ethereal' not in headline(triage | {'ethereal_basis': None})
