import argparse

from inventory_tracking.routes import table
from inventory_tracking.routes.catalog import EXEMPT, ROUTES
from inventory_tracking.routes.check import problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=table.__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--write', action='store_true', help='put the tables into levels/routes.md')
    args = parser.parse_args(argv)
    found = problems(ROUTES, EXEMPT)
    for problem in found:
        print(f'PROBLEM: {problem}')
    tables = table.render(ROUTES)
    if args.write:
        table.DOCUMENT.write_text(table.embed(table.DOCUMENT.read_text(), tables))
    else:
        print(tables)
    return 1 if found else 0


if __name__ == '__main__':
    raise SystemExit(main())
