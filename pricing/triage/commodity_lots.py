"""Keep per-unit quotes distinct from the value of a fungible sale lot."""


def fungible(item):
    category, name = item.get('category'), str(item.get('name', '')).casefold()
    return (category == 'runes' and name.endswith(' rune')) or (category == 'gems' and name != 'random gems')


def sale_value(item, unit_price):
    quantity = item.get('quantity', 1)
    if fungible(item) and type(quantity) is int and quantity > 1 and type(unit_price) in (int, float):
        return unit_price * quantity
    return unit_price


def compile_lots(bands, keep_ist):
    groups = {}
    for (category, name, _), band in bands.items():
        quantity, price = band.get('quantity'), band.get('q1_ist')
        if (
            fungible({'category': category, 'name': name})
            and type(quantity) is int
            and quantity > 1
            and type(price) in (int, float)
            and price > 0
            and price * quantity >= keep_ist
            and band.get('sellers', 0) >= 3
            and band.get('liquidity') in ('liquid', 'thin')
        ):
            groups.setdefault((category, name), []).append(band)
    return {
        key: sorted(rows, key=lambda b: (b['liquidity'] != 'liquid', b['quantity'])) for key, rows in groups.items()
    }


def available_lots(item, tables):
    quantity = item.get('quantity', 1)
    if not fungible(item) or type(quantity) is not int or quantity < 1:
        return []
    index = tables.get('commodity_lots')
    if index is None:
        index = compile_lots(tables['bands'], tables['rules']['keep_ist'])
    return index.get((item['category'], item['name'].casefold()), [])


def sale_lot(item, tables):
    return next((b for b in available_lots(item, tables) if b['quantity'] <= item.get('quantity', 1)), None)


def accumulation(item, tables):
    return next((b for b in available_lots(item, tables) if b['quantity'] > item.get('quantity', 1)), None)


def saving_reason(band):
    quantity, price = band['quantity'], band['q1_ist']
    return (
        f'save toward a lot of {quantity} — asks {price * quantity:.3g} Ist per lot '
        f'({price:.3g} Ist each) · {band["sellers"]} sellers · {band.get("observed_at") or "undated"}'
    )
