"""Reviewed homogeneous materials; recipe bundles and variable uniques stay separate."""

# Native identities: third-parties/d2data/json/misc.json and allstrings-eng.json.
# Market IDs: appraisal-traderie-catalog.json, reviewed 2026-10-06.
MATERIAL_CATALOG = {
    'burning essence of terror': '4236249228',
    "baal's eye": '2655337846',
    'charged essence of hatred': '2952287395',
    "diablo's horn": '4017446841',
    'festering essence of destruction': '3727189878',
    "mephisto's brain": '4156171711',
    'key of terror': '3117972750',
    'key of hate': '2324195166',
    'key of destruction': '2841933158',
    'full rejuvenation potion': '2483707607',
    'rejuvenation potion': '2235187003',
    'standard of heroes': '3884330429',
    'twisted essence of suffering': '2406244331',
    'token of absolution': '3193724423',
    "talic's anguish": '700449418',
    "korlic's pain": '1526346808',
    "madawc's ire": '1806446366',
    "bul-kathos' nightmare": '169558979',
    "worusk's end": '1055348421',
    'western worldstone shard': '1189945720',
    'eastern worldstone shard': '901913969',
    'southern worldstone shard': '1662925107',
    'deep worldstone shard': '1395991248',
    'northern worldstone shard': '399128412',
}


# Native rpot codes; do not classify other potions or weapons by quantity alone.
MATERIAL_POTIONS = frozenset({'rvl', 'rvs'})


def material_lot(name, category, listing):
    return (
        category == 'misc'
        and MATERIAL_CATALOG.get(name.casefold()) == str(listing.get('item_id'))
        and listing.get('stock') is False
        and type(listing.get('amount')) is int
        and listing['amount'] > 0
    )
