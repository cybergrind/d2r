"""Standard Hellwarden and MF Harlequin recipients from the actual guide variants.

Loose components do not establish socket ownership or a complete setup. Blessed
Hammer benefits from magic spell damage and pierce; triggered effects are separate.
"""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_guardian_components import cases


CASES = tuple(
    cases(
        build='blessed-hammer-paladin',
        player_class='Paladin',
        prefix='hammer',
        recipients=((1, "Hellwarden's Will", 'Harlequin Crest'), (2, 'Harlequin Crest', "Hellwarden's Will")),
    )
)
