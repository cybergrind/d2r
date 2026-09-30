"""Witness one existing base/ethereal alternative without changing runtime rules."""


def equipment_branch(predicate, selections):
    if not isinstance(selections, dict) or not selections:
        raise ValueError('Equipment branch selections must be a nonempty path map')
    consumed = set()

    def visit(node, path):
        if path in selections:
            index = selections[path]
            children = node.get('any')
            if (
                not equipment_only(node)
                or not isinstance(children, list)
                or type(index) is not int
                or not 0 <= index < len(children)
            ):
                raise ValueError('Equipment branch must select an existing base/ethereal alternative')
            consumed.add(path)
            return visit(children[index], f'{path}/any/{index}')
        for op in ('all', 'any'):
            if set(node) == {op}:
                return {op: [visit(child, f'{path}/{op}/{i}') for i, child in enumerate(node[op])]}
        return dict(node)

    result = visit(predicate, '')
    if consumed != set(selections):
        raise ValueError('Equipment branch path is missing or outside the selected alternative')
    return result


def equipment_only(node):
    for op in ('all', 'any'):
        if set(node) == {op}:
            return isinstance(node[op], list) and bool(node[op]) and all(equipment_only(child) for child in node[op])
    return (
        set(node) == {'op', 'field', 'value'}
        and node['op'] == 'fact_eq'
        and (
            (node['field'] == 'base_code' and isinstance(node['value'], str) and bool(node['value']))
            or (node['field'] == 'ethereal' and type(node['value']) is bool)
        )
    )
