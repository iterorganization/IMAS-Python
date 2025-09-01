import imas
from imas.util import find_paths
import re
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="List IDS paths that have name+identifier but are not full identifier structs"
    )
    parser.add_argument(
        "-v",
        "--version",
        default="4.0.0",
        help="Data dictionary version to use (default: 4.0.0)",
    )
    args = parser.parse_args()

    cp = imas.IDSFactory(args.version)
    ids_list = cp.ids_names()

    for ids_name in ids_list:
        obj = cp.new(ids_name)
        # Find parents that have both 'name' and 'identifier' children
        name_paths = find_paths(obj, "(^|/)name$")
        id_paths = find_paths(obj, "(^|/)identifier$")

        def parent_of(p):
            return p.rsplit('/', 1)[0] if '/' in p else ''

        name_parents = set(parent_of(p) for p in name_paths)
        id_parents = set(parent_of(p) for p in id_paths)

        both_parents = sorted(name_parents & id_parents)
        filtered = []
        for parent in both_parents:
            # build sibling full paths
            def full(p):
                return f"{parent}/{p}" if parent else p

            has_index = bool(find_paths(obj, f'^{re.escape(full("index"))}$'))
            has_desc = bool(find_paths(obj, f'^{re.escape(full("description"))}$'))

            # Exclude parents that have name + index + description (full identifier struct)
            if has_index and has_desc:
                continue
            filtered.append(parent)

        if filtered:
            print(ids_name, filtered)


if __name__ == "__main__":
    main()

