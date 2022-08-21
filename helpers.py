import json
from typing import List

from config import FIND_CONTAINING_MODULES_DEPTH, PRINT_QUERIES, QUERY_FILE_PATH


def write_queries_to_file(module_name: str, content: str) -> None:
    module_name = module_name.replace("/", "-")
    module_name = module_name.replace(".htm", "")

    file = open(QUERY_FILE_PATH.format(module_name=module_name), "w")
    file.write(content)
    file.close()


def dump_list(query_list: list, print_content: bool) -> None:
    content = ""
    module_name = query_list[0]["module_name"] if query_list else ""
    for query in query_list:
        content += 100 * "-"
        content += query["module_name"]
        content += 100 * "-"
        content += "\n\n"
        for key, value in query.items():
            # Print Table Information
            if key.startswith("TABLE"):
                content += "\t\t" + (50 * "*") + " TABLE " + (50 * "*") + "\n\n\n"
                content += "\t\tTable Name: {}".format(key.split("-")[1])
                content += "\t\tFields: {}".format(value)
                content += "\n\n"
            # Print Query Information
            elif key == "queries" and PRINT_QUERIES:
                content += "\t\t" + (50 * "*") + " QUERIES " + (50 * "*") + "\n\n\n"
                for q in value:
                    content += "\t\t" + q
                    content += "\n\n"
            # Print Content Information
            elif key == "content" and print_content:
                content += "\t\t" + (50 * "*") + " CONTENT " + (50 * "*") + "\n\n\n"
                content += "\t\t" + value
                content += "\n\n"
            elif key.startswith("MEMBER"):
                content += "\t\t" + (50 * "*") + " MEMBER " + (50 * "*") + "\n\n\n"
                content += "\t\t{}: {}".format(key.split("-")[1], value)
                content += "\n\n"

    # Print Module Call Tree
    content += (50 * "*") + " MODULE CALL TREE " + (50 * "*")
    content += "\t\t\n\n\n"
    for data in map(lambda q: {q["module_name"]: q["called_modules"]}, query_list):
        data_content = json.dumps(data)
        content += data_content

    write_queries_to_file(module_name, content)


def print_run_context(
    input_term: List[str],
    selection: str,
    find_tables: bool,
    find_containing_modules: bool,
    print_content: bool,
) -> None:
    print("\n")
    print(100 * "*")

    on = "\033[1mON\033[0m"
    off = "\033[1mOFF\033[0m"

    if selection == "p":
        print("Will parse the {} module.".format(input_term))
        if find_containing_modules:
            module_switch = on
        else:
            module_switch = off
        print("Finding containing modules switch: {}".format(module_switch))
        print(
            "Will find this many modules including itself: \033[1m{}\033[0m".format(
                FIND_CONTAINING_MODULES_DEPTH
            )
        )

        if find_tables:
            table_switch = on
        else:
            table_switch = off
        print("Finding tables switch: {}".format(table_switch))

        if PRINT_QUERIES:
            query_switch = on
        else:
            query_switch = off
        print("Print queries switch: {}".format(query_switch))

        if print_content:
            content_switch = on
        else:
            content_switch = off
        print("Print content switch: {}".format(content_switch))
    print(100 * "*")
    print("\n")
