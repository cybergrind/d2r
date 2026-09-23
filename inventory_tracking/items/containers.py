"""Player inventory pages verified by native widget/grid host captures."""


def container_for_page(page, *, owner_type=0):
    if owner_type == 1 and page == 255:
        return {'page': page, 'name': 'Mercenary equipment'}
    if owner_type == 1 and type(page) is int and 0 <= page <= 3:
        return {'page': page, 'name': 'Shop inventory'}
    names = {0: 'Main inventory', 3: 'Horadric Cube', 4: 'Stash', 255: 'Equipped items'}
    if owner_type != 0:
        raise ValueError('Unsupported inventory owner type')
    if type(page) is not int or page not in names:
        raise ValueError('Unsupported inventory container')
    return {'page': page, 'name': names[page]}
