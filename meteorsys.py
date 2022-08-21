import re
import sys
from typing import Optional

import requests
from requests import Response

from config import (
    CONTENT_LIBRARY_REGEX,
    CONTENT_LIBRARY_WORD,
    CONTENT_URL,
    FIND_CONTAINING_MODULES_DEPTH,
    FOLDER_NAMES,
    LIST_CONTENTS_URL,
    LOGIN_URL,
    PASSWORD,
    QUERY_REGEX,
    RESPONSYS_AUTH_TOKEN_KEY,
    TABLE_MEMBERS_URL,
    TABLE_REGEX,
    TABLE_URL,
    TABLES_TO_QUERIES_DICT,
    TOKEN_EXPIRATION_SECONDS,
    USERNAME,
)
from decorators import get_from_redis_or_set
from exceptions import RequestFailedException, TokenException, TokenExpiredException
from helpers import dump_list, print_run_context, write_queries_to_file
from redis_ops import get_from_redis, save_to_redis

# TODO: If no running Redis, ImproperlyConfigured should be raised


class ResponsysParser:
    def __init__(self, parser_client):
        self.parser_client = parser_client
        self.token = self.get_auth_token()

    def is_success(self, response: Response) -> bool:
        if response.ok:
            return True
        return False

    def check_response(self, response: Response) -> None:
        if not self.is_success(response):
            if response.status_code == 401:
                raise TokenExpiredException
            raise RequestFailedException

    def get_auth_token(self) -> str:
        token = get_from_redis(RESPONSYS_AUTH_TOKEN_KEY)
        if not token:
            data = {
                "user_name": USERNAME,
                "password": PASSWORD,
                "auth_type": "password",
            }
            response = requests.post(LOGIN_URL, data=data)
            if not self.is_success(response):
                raise TokenException
            token = response.json()["authToken"]
            save_to_redis(RESPONSYS_AUTH_TOKEN_KEY, token, ex=TOKEN_EXPIRATION_SECONDS)
        return token

    @get_from_redis_or_set
    def get_content(self, module_name: str) -> Optional[str]:
        headers = {"Authorization": self.token, "Content-Type": "application/json"}
        url = "{base_url}/{module_name}".format(
            base_url=CONTENT_URL, module_name=module_name
        )
        response = requests.get(url, headers=headers)
        self.check_response(response)
        content = response.json()["content"]
        return content

    def get_table(self, folder_name: str, table_name: str):
        headers = {"Authorization": self.token, "Content-Type": "application/json"}
        url = TABLE_URL.format(folder_name=folder_name, table_name=table_name)
        response = requests.get(url, headers=headers)

        if self.is_success(response):
            return response.json()["fields"]

    def build_table_query(self, table_name: str) -> Optional[str]:
        table_query_dict = self.get_table_query_dict(table_name)
        if not table_query_dict:
            return None
        queries = []
        for qa, qv in table_query_dict["qav"].items():
            queries.append("qa={qa}&id={qv}".format(qa=qa, qv=qv))
        fs = table_query_dict["fs"]
        queries.append("fs={fs}".format(fs=fs))
        return "&".join(queries)

    def get_table_query_dict(self, table_name: str) -> Optional[dict]:
        try:
            return TABLES_TO_QUERIES_DICT[table_name]
        except KeyError:
            return None

    def get_table_member(self, table_name: str) -> Optional[dict]:
        headers = {"Authorization": self.token, "Content-Type": "application/json"}
        query = self.build_table_query(table_name)
        if not query:
            return None

        url = TABLE_MEMBERS_URL.format(table_name=table_name, query=query)
        response = requests.get(url, headers=headers)

        if self.is_success(response):
            return response.json()["recordData"]["records"][0][0]

        return None

    def get_contents_of_folder(self, folder_name):
        headers = {"Authorization": self.token, "Content-Type": "application/json"}

        url = LIST_CONTENTS_URL.format(folder_name=folder_name, type="docs")
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            documents = response.json()["documents"]
            document_paths = list(map(lambda d: d["documentPath"], documents))
            return document_paths

    def execute(self) -> None:
        if not self.parser_client:
            return None
        print("Parser is working its magic...")
        return self.parser_client.execute()


class ResponsysModuleParser(ResponsysParser):
    def __init__(self, module_names=None, **kwargs):
        super().__init__(self)
        self.module_names = module_names
        self.depth = 1
        self.find_containing_modules = kwargs["find_containing_modules"]
        self.find_tables = kwargs["find_tables"]
        self.print_content = kwargs["print_content"]

    def has_containing_modules(self, content: str) -> bool:
        return CONTENT_LIBRARY_WORD in content

    def build_module_regex_from_content(self, content: str) -> str:
        initial_regex = r"^.*{cgs}$"
        word_count = content.count(CONTENT_LIBRARY_WORD)
        final_regex = initial_regex.format(cgs=word_count * CONTENT_LIBRARY_REGEX)
        return final_regex

    def parse_module(self, content: str) -> Optional[list]:
        if not self.has_containing_modules(content):
            return None

        use_regex = self.build_module_regex_from_content(content)
        modules = []

        # unicode escape
        content = content.encode("unicode_escape").decode("utf-8")

        matches = re.finditer(use_regex, content, re.MULTILINE)

        for _, match in enumerate(matches, start=1):
            for group_num in range(0, len(match.groups())):
                group_num = group_num + 1
                modules.append(match.group(group_num))
        return modules

    @staticmethod
    def parse_queries(content: str):
        """Parses for Responsys queries in the given HTML content"""
        result = re.findall(QUERY_REGEX, content)
        return result

    @staticmethod
    def parse_table_information(query: str) -> list:
        """Tries to parse a table from the passed in Responsys query"""
        matches = []
        for match in re.finditer(TABLE_REGEX, query, re.IGNORECASE):
            group_dict = match.groupdict()
            folder_name = group_dict["folder_name"]
            table_name = group_dict["table_name"]
            qa = group_dict["qa"] if group_dict["qa"] != "LANG" else group_dict["qa2"]
            qv = group_dict["qv"] if group_dict["qv"] != "LANG" else group_dict["qv2"]

            data = {
                "folder_name": folder_name,
                "table_name": table_name,
                "qa": qa,
                "qv": qv,
            }
            matches.append(data)
        return matches

    @staticmethod
    def build_module_path(module_name: str) -> str:
        """Returns module path like contentlibrary/folder/abc.htm"""
        module_name = module_name.strip()
        content_pos = module_name.find("contentlibrary")
        comma_pos = module_name.find(",")
        first = module_name[content_pos:comma_pos]
        second = module_name[comma_pos + 1 :]
        return "{}/{}".format(first.strip(), second.strip())

    def parse_table(self, queries: list) -> dict:
        data = {}
        for query in queries:
            table_informations = self.parse_table_information(query)
            if table_informations:
                for table_information in table_informations:
                    folder_name, table_name, qa, qv = (
                        table_information["folder_name"],
                        table_information["table_name"],
                        table_information["qa"],
                        table_information["qv"],
                    )

                    if all((folder_name, table_name)):
                        fields = self.get_table(folder_name, table_name)
                        data["TABLE-{}".format(table_name)] = fields

                    if all((qa, qv)):
                        member_result = self.get_table_member(table_name)
                        if member_result:
                            data["MEMBER-{}".format(qv)] = member_result
        return data

    def parse_content(self, module_name: str, depth: int = 1):
        """Parses all the content and return all the Responsys Queries"""

        list_of_queries = []

        try:
            content = self.get_content(module_name)
        except Exception:
            print("Request failed, continuing...")
            content = None

        if not content:
            print("No content found for module: {}".format(module_name))
            return list_of_queries

        module_paths = None
        if self.find_containing_modules and depth != FIND_CONTAINING_MODULES_DEPTH:
            content_module_names = self.parse_module(content)

            if content_module_names:
                module_paths = [
                    self.build_module_path(content_module_name)
                    for content_module_name in content_module_names
                ]
                depth += 1

                for module_path in module_paths:
                    list_of_queries.extend(self.parse_content(module_path, depth=depth))

        queries = self.parse_queries(content)
        data = {
            "module_name": module_name,
            "queries": queries,
            "content": content,
            "called_modules": module_paths,
        }

        if self.find_tables:
            table_data = self.parse_table(queries)
            data = {**data, **table_data}

        list_of_queries.append(data)

        return list_of_queries

    def execute(self):
        for module_name in self.module_names:
            list_of_queries = self.parse_content(module_name, self.depth)
            dump_list(list_of_queries, self.print_content)
        print("Finished parsing {module_names}".format(module_names=self.module_names))


class ResponsysFolderScanner(ResponsysModuleParser):
    def __init__(self, keyword, folder_names):
        super().__init__(
            self, find_containing_modules=False, print_content=False, find_tables=False
        )
        self.keyword = keyword
        self.folder_names = folder_names

    def scan_folder_for_keyword(self, keyword, folder_names):
        module_names_string = ""
        for folder_name in folder_names:
            module_names_string += "--- " + folder_name + " ---" + "\n\n\n\n"
            print("Scanning {folder_name} now...".format(folder_name=folder_name))
            print(100 * "*")
            module_names = self.get_contents_of_folder(folder_name)
            if not module_names:
                print("No module names found!")
                continue
            for module_name in module_names:
                list_of_queries = self.parse_content(module_name, depth=1)
                if not list_of_queries:
                    print("No query found!")
                    continue
                queries = list_of_queries[0]["queries"]
                for query in queries:
                    if keyword in query:
                        print(100 * "-")
                        print(module_name)
                        module_names_string += module_name + "\n\n"
                        print(100 * "-")
                        break
            module_names_string += "\n\n"
        write_queries_to_file(keyword, module_names_string)

    def execute(self):
        self.scan_folder_for_keyword(self.keyword, self.folder_names)


def get_input_modules():
    input_modules = str(input("Enter the input module names (,): "))
    return input_modules.split(", ")


def get_folder_name():
    return str(input("Enter the folder name: "))


def get_switches():
    find_tables = True if str(input("Find tables? : ")) in ("y", "Y") else False
    print_content = True if str(input("Print content? : ")) in ("y", "Y") else False
    find_containing_modules = (
        True if str(input("Find containing modules? : ")) in ("y", "Y") else False
    )
    return find_tables, print_content, find_containing_modules


def get_proceed():
    proceed = input(
        "\033[1mDo you want to continue with the above settings? "
        "(Y/y to proceed, N/n to stop) \033[0m"
    )
    return proceed


def main():
    selection = str(input("Enter option: (parse content (p) | scan for keyword (s) "))
    if selection == "p":
        input_modules = get_input_modules()
        folder_name = get_folder_name()

        module_list = [
            "/contentlibrary/{folder_name}/{input_module}.htm".format(
                folder_name=folder_name, input_module=input_module
            )
            for input_module in input_modules
        ]

        find_tables, print_content, find_containing_modules = get_switches()

        print_run_context(
            input_modules,
            selection,
            find_tables,
            find_containing_modules,
            print_content,
        )
        proceed = get_proceed()

        if proceed == "N" or proceed == "n":
            print("Shutting down: Terminated by user")
            sys.exit(0)

        parser_client = ResponsysModuleParser(
            module_names=module_list,
            find_containing_modules=find_containing_modules,
            find_tables=find_tables,
            print_content=print_content,
        )
    elif selection == "s":
        keyword = "EMAIL_ADDRESS_"
        parser_client = ResponsysFolderScanner(
            keyword=keyword, folder_names=FOLDER_NAMES
        )
    else:
        sys.exit(0)

    responsys_parser = ResponsysParser(parser_client=parser_client)
    responsys_parser.execute()


if __name__ == "__main__":
    main()
