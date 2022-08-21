from unittest import TestCase
from unittest import main as unittest_main
from unittest import mock

import fakeredis
from decouple import config

from config import (
    CONTENT_URL,
    LIST_CONTENTS_URL,
    LOGIN_URL,
    QUERY_FILE_PATH,
    RESPONSYS_AUTH_TOKEN_KEY,
    TABLE_MEMBERS_URL,
    TABLE_URL,
)
from exceptions import TokenExpiredException
from fixtures import (
    CONTENT_RESPONSE,
    CONTENT_RESPONSES,
    LIST_CONTENTS_RESPONSE,
    TABLE_MEMBERS_RESPONSE,
    TABLE_RESPONSE,
    TOKEN_EXPIRED_RESPONSE,
)
from helpers import dump_list, print_run_context, write_queries_to_file
from meteorsys import (
    ResponsysFolderScanner,
    ResponsysModuleParser,
    ResponsysParser,
    get_folder_name,
    get_input_modules,
    get_proceed,
    get_switches,
    main,
)

fake_redis = fakeredis.FakeRedis()


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    @property
    def ok(self):
        return self.status_code == 200

    def json(self):
        return self.json_data


def mocked_post_request(*args, **kwargs):
    if args[0] == LOGIN_URL:
        return MockResponse({"authToken": "token"}, 200)


def mocked_get_request(*args, **kwargs):
    if CONTENT_URL in args[0]:
        url = args[0]
        module_name = url[url.rfind("/") + 1 :]
        json_data = CONTENT_RESPONSES.get(module_name, {})
        return MockResponse(json_data, 200)
    elif TABLE_MEMBERS_URL in args[0] or "members" in args[0]:
        return MockResponse(TABLE_MEMBERS_RESPONSE, 200)
    elif TABLE_URL in args[0] or "suppData" in args[0]:
        return MockResponse(TABLE_RESPONSE, 200)
    elif LIST_CONTENTS_URL in args[0] or "clFolders" in args[0]:
        return MockResponse(LIST_CONTENTS_RESPONSE, 200)


def mocked_failed_get_request(*args, **kwargs):
    return MockResponse(TOKEN_EXPIRED_RESPONSE, 401)


def mock_get_contents_of_folder(self, folder_name):
    return


def mock_parse_content(self, module_name, depth=1):
    return


@mock.patch("redis_ops.redis_client", fake_redis)
@mock.patch("requests.post", side_effect=mocked_post_request)
class TestResponsysParser(TestCase):
    def test_init_sets_client_and_token(self, m_post):
        """
        Test that it can initialize the parser_client & token
        """
        parser = ResponsysParser(None)
        self.assertIsNotNone(parser.token)
        call_args_list = m_post.call_args_list
        self.assertEqual(call_args_list[0][0][0], LOGIN_URL)
        self.assertEqual(call_args_list[0][1]["data"]["user_name"], config("USERNAME"))
        self.assertEqual(call_args_list[0][1]["data"]["password"], config("PASSWORD"))

    @mock.patch("requests.get", side_effect=mocked_get_request)
    def test_get_content_correctly_returns_html_content(self, m_get, m_post):
        """
        Test that it can correctly return the html content
        """

        parser = ResponsysParser(None)
        content = parser.get_content("generic.htm")
        self.assertEqual(content, CONTENT_RESPONSE["content"])

    @mock.patch("decorators.get_from_redis", side_effect=lambda key: None)
    @mock.patch("requests.get", side_effect=mocked_failed_get_request)
    def test_get_content_raises_token_expired_when_status_code_is_401(
        self, m_get_from_redis, m_get, m_post
    ):
        """
        Test that it can correctly return the html content
        """

        parser = ResponsysParser(None)
        with self.assertRaises(TokenExpiredException):
            parser.get_content("generic.htm")

    @mock.patch("requests.get", side_effect=mocked_get_request)
    def test_get_table_correctly_returns_fields_content(self, m_get, m_post):
        """
        Test that it can correctly return fields content
        """

        parser = ResponsysParser(None)
        fields = parser.get_table("folder", "USERS")
        self.assertEqual(fields, TABLE_RESPONSE["fields"])

    @mock.patch("requests.get", side_effect=mocked_get_request)
    @mock.patch("meteorsys.TABLES_TO_QUERIES_DICT", return_value=mock.MagicMock())
    def test_get_table_members_correctly_returns_members_content(
        self, m_dict, m_get, m_post
    ):
        """
        Test that it can correctly return table members content
        """

        d = {"ALL_USERS": {"fs": "TITLE", "qav": {"ID": "1"}}}
        m_dict.__getitem__.side_effect = d.__getitem__
        parser = ResponsysParser(None)
        table_members = parser.get_table_member("ALL_USERS")

        # Then
        self.assertTrue("qa=ID" in m_get.call_args_list[0][0][0])
        self.assertTrue("id=1" in m_get.call_args_list[0][0][0])
        self.assertTrue("fs=TITLE" in m_get.call_args_list[0][0][0])
        self.assertTrue("ALL_USERS" in m_get.call_args_list[0][0][0])
        self.assertEqual(table_members, "John Doe")

    def tearDown(self):
        fake_redis.delete(RESPONSYS_AUTH_TOKEN_KEY)


@mock.patch("redis_ops.redis_client", fake_redis)
@mock.patch("requests.post", side_effect=mocked_post_request)
class TestResponsysModuleParser(TestCase):
    @mock.patch("requests.get", side_effect=mocked_get_request)
    def test_parse_content_correctly_parses_queries_wo_recursion(self, m_get, m_post):
        """
        Test that it can parse the data
        """
        parser_client = ResponsysModuleParser(
            module_names=["generic.htm"],
            find_containing_modules=False,
            find_tables=False,
            print_content=False,
        )
        list_of_queries = parser_client.parse_content("generic.htm", 1)
        query_data = list_of_queries[0]
        self.assertEqual(query_data["module_name"], "generic.htm")
        expected = (
            "$LOOKUP(SOMEVARIABLE)$?$LOOKUP(VARIABLE)$&amp;utm_term=$LOOKUP(MODULE)"
        )
        self.assertEqual(query_data["queries"][0], expected)
        self.assertIsNone(query_data["called_modules"])

    @mock.patch("requests.get", side_effect=mocked_get_request)
    def test_parse_content_correctly_parses_queries_with_recursion(self, m_get, m_post):
        """
        Test that it can parse the data with containing modules
        """
        parser_client = ResponsysModuleParser(
            module_names=["generic.htm"],
            find_containing_modules=True,
            find_tables=False,
            print_content=False,
        )
        list_of_queries = parser_client.parse_content("containing.htm", 1)
        contained_query_data = list_of_queries[0]
        self.assertEqual(
            contained_query_data["module_name"], "contentlibrary/modules/contained.htm"
        )
        expected = "$SETVARS(VARLIST(1, USERS, LOOKUPRECORDS(!MasterData, ALL_USERS, PAIRS(RIID_, LOOKUP(RIID_), ID, LOOKUP(ID)), TITLE)))"
        self.assertEqual(contained_query_data["queries"][0], expected)

    @mock.patch("requests.get", side_effect=mocked_get_request)
    def test_parse_content_correctly_parses_queries_with_recursion_find_tables(
        self, m_get, m_post
    ):
        """
        Test that it can parse the data with containing modules
        """
        parser_client = ResponsysModuleParser(
            module_names=["generic.htm"],
            find_containing_modules=True,
            find_tables=True,
            print_content=False,
        )
        list_of_queries = parser_client.parse_content("containing.htm", 1)
        contained_query_data = list_of_queries[0]
        containing_query_data = list_of_queries[1]
        self.assertEqual(
            contained_query_data["module_name"], "contentlibrary/modules/contained.htm"
        )
        expected = "$SETVARS(VARLIST(1, USERS, LOOKUPRECORDS(!MasterData, ALL_USERS, PAIRS(RIID_, LOOKUP(RIID_), ID, LOOKUP(ID)), TITLE)))"
        self.assertEqual(contained_query_data["queries"][0], expected)

        self.assertTrue("TABLE-ALL_USERS" in contained_query_data.keys())
        self.assertEqual(
            contained_query_data["TABLE-ALL_USERS"], TABLE_RESPONSE["fields"]
        )

    @mock.patch("decorators.get_from_redis", side_effect=lambda key: None)
    @mock.patch("requests.get")
    def test_parse_content_handles_exception(self, m_get, m_get_from_redis, m_post):
        """
        Test that it can parse the data
        """

        m_get.side_effect = ConnectionError
        m_get_from_redis.return_value = None

        parser_client = ResponsysModuleParser(
            module_names=["generic.htm"],
            find_containing_modules=False,
            find_tables=False,
            print_content=False,
        )
        list_of_queries = parser_client.parse_content("generic.htm", 1)

        self.assertEqual(list_of_queries, [])

    def tearDown(self):
        fake_redis.delete(RESPONSYS_AUTH_TOKEN_KEY)


@mock.patch("redis_ops.redis_client", fake_redis)
class TestResponsysFolderScanner(TestCase):
    @mock.patch("meteorsys.write_queries_to_file")
    @mock.patch("requests.get", side_effect=mocked_get_request)
    def test_folder_scanner_success(self, m_get, m_write):
        parser_client = ResponsysFolderScanner(
            keyword="SOMEVARIABLE", folder_names=["modules"]
        )
        parser_client.execute()
        write_call_args = m_write.call_args_list[0][0]
        self.assertEqual(write_call_args[0], "SOMEVARIABLE")
        self.assertTrue("generic.htm" in write_call_args[1])

    @mock.patch("meteorsys.write_queries_to_file")
    @mock.patch("requests.get", side_effect=mocked_get_request)
    def test_folder_scanner_with_empty_folder_content(self, m_get, m_write):
        with mock.patch.object(
            ResponsysFolderScanner,
            "get_contents_of_folder",
            mock_get_contents_of_folder,
        ):
            parser_client = ResponsysFolderScanner(
                keyword="SOMEVARIABLE", folder_names=["modules"]
            )
            parser_client.execute()
            m_get.assert_not_called()
            write_call_args = m_write.call_args_list[0][0]
            self.assertEqual(write_call_args[0], "SOMEVARIABLE")
            self.assertTrue("generic.htm" not in write_call_args[1])

    @mock.patch("meteorsys.write_queries_to_file")
    @mock.patch("requests.get", side_effect=mocked_get_request)
    def test_folder_scanner_with_parse_content_failure(self, m_get, m_write):
        with mock.patch.object(
            ResponsysFolderScanner, "parse_content", mock_parse_content
        ):
            parser_client = ResponsysFolderScanner(
                keyword="SOMEVARIABLE", folder_names=["modules"]
            )
            parser_client.execute()
            m_get.assert_called()
            write_call_args = m_write.call_args_list[0][0]
            self.assertEqual(write_call_args[0], "SOMEVARIABLE")
            self.assertTrue("generic.htm" not in write_call_args[1])


@mock.patch("redis_ops.redis_client", fake_redis)
@mock.patch("meteorsys.get_input_modules")
@mock.patch("meteorsys.get_folder_name")
@mock.patch("meteorsys.get_switches")
@mock.patch("meteorsys.get_proceed")
@mock.patch("helpers.write_queries_to_file")
@mock.patch("requests.post", side_effect=mocked_post_request)
@mock.patch("requests.get", side_effect=mocked_get_request)
class TestMain(TestCase):
    def test_main(
        self, m_get, m_post, m_write, m_proceed, m_switches, m_folder, m_modules
    ):
        # Given
        m_modules.return_value = ["generic"]
        m_folder.return_value = "modules"
        # Stands for find_tables, print_content and find_containing_modules
        m_switches.return_value = (True, True, True)
        m_proceed.return_value = "Y"

        # When
        main()

        # Then

        # Post assertions
        post_call_args_list = m_post.call_args_list
        self.assertEqual(post_call_args_list[0][0][0], LOGIN_URL)
        self.assertEqual(post_call_args_list[0][0][0], LOGIN_URL)
        self.assertEqual(
            post_call_args_list[0][1]["data"]["user_name"], config("USERNAME")
        )
        self.assertEqual(
            post_call_args_list[0][1]["data"]["password"], config("PASSWORD")
        )

        # Get assertions
        get_call_args_list = m_get.call_args_list
        get_url = get_call_args_list[0][0][0]
        last_slash_index = get_url.rfind("/")
        self.assertEqual(get_url[last_slash_index + 1 :], "generic.htm")

        # Write assertions
        write_call_args_list = m_write.call_args_list
        module_name = write_call_args_list[0][0][0]
        self.assertEqual(module_name, "/contentlibrary/modules/generic.htm")
        content = write_call_args_list[0][0][1]
        self.assertTrue(
            "$LOOKUP(SOMEVARIABLE)$?$LOOKUP(VARIABLE)$&amp;utm_term=$LOOKUP(MODULE)"
            in content
        )
        self.assertTrue('{"/contentlibrary/modules/generic.htm": null}' in content)

    @mock.patch("meteorsys.sys.exit")
    def test_main_no_proceed(
        self, m_sys, m_get, m_post, m_write, m_proceed, m_switches, m_folder, m_modules
    ):
        # Given
        m_modules.return_value = ["generic"]
        m_folder.return_value = "modules"
        # Stands for find_tables, print_content and find_containing_modules
        m_switches.return_value = (True, True, True)
        m_proceed.return_value = "N"

        # When
        main()

        # Then
        m_sys.assert_called()

    def test_get_switches(
        self, m_get, m_post, m_write, m_proceed, m_switches, m_folder, m_modules
    ):
        with mock.patch("builtins.input") as m_input:
            m_input.return_value = "y"
            find_tables, print_content, find_containing_modules = get_switches()
        self.assertTrue(find_tables)
        self.assertTrue(print_content)
        self.assertTrue(find_containing_modules)

    def test_get_input_modules(
        self, m_get, m_post, m_write, m_proceed, m_switches, m_folder, m_modules
    ):
        with mock.patch("builtins.input") as m_input:
            m_input.return_value = "generic, generictwo"
            input_modules = get_input_modules()
        self.assertEqual(input_modules, ["generic", "generictwo"])

    def test_get_folder_name(
        self, m_get, m_post, m_write, m_proceed, m_switches, m_folder, m_modules
    ):
        with mock.patch("builtins.input") as m_input:
            m_input.return_value = "modules"
            folder_name = get_folder_name()
        self.assertEqual(folder_name, "modules")

    def test_get_proceed_false(
        self, m_get, m_post, m_write, m_proceed, m_switches, m_folder, m_modules
    ):
        with mock.patch("builtins.input") as m_input:
            m_input.return_value = "n"
            proceed = get_proceed()
        self.assertEqual(proceed, "n")

    def test_get_proceed_true(
        self, m_get, m_post, m_write, m_proceed, m_switches, m_folder, m_modules
    ):
        with mock.patch("builtins.input") as m_input:
            m_input.return_value = "y"
            proceed = get_proceed()
        self.assertEqual(proceed, "y")


class TestHelpers(TestCase):
    def test_write_queries_to_file(self):
        with mock.patch("builtins.open", mock.mock_open()) as m:
            write_queries_to_file("MockModule", "Mock Content")

        m.assert_called_once_with(QUERY_FILE_PATH.format(module_name="MockModule"), "w")
        handle = m()
        handle.write.assert_called_once_with("Mock Content")

    @mock.patch("helpers.write_queries_to_file")
    def test_dump_list_dumps_query_information(self, m_write):
        # Given
        query_list = [
            {
                "module_name": "generic.htm",
                "queries": ["$LOOKUP(MODULENAME)$", "$LOOKUP(VARIABLE)$"],
                "called_modules": None,
            }
        ]
        # When
        dump_list(query_list, False)
        # Then
        self.assertEqual(m_write.call_args_list[0][0][0], "generic.htm")
        content = m_write.call_args_list[0][0][1]
        self.assertTrue(query_list[0]["queries"][0] in content)
        self.assertTrue(query_list[0]["queries"][1] in content)
        self.assertTrue('{"generic.htm": null}' in content)

    @mock.patch("helpers.write_queries_to_file")
    def test_dump_list_with_table_dumps_table_information(self, m_write):
        # Given
        query_list = [
            {
                "module_name": "generic.htm",
                "queries": [
                    "$LOOKUP(MODULENAME)$",
                    "$LOOKUP(VARIABLE)$, $LOOKUPTABLE(!Data, ALL_USERS, ID, LOOKUP(ID), TITLE)$",
                ],
                "called_modules": None,
                "TABLE-ALL_USERS": '{"fieldName": "TITLE", "fieldType": "STR500"}',
            }
        ]
        # When
        dump_list(query_list, False)
        # Then
        self.assertEqual(m_write.call_args_list[0][0][0], "generic.htm")
        content = m_write.call_args_list[0][0][1]
        self.assertTrue("Table Name: ALL_USERS" in content)
        self.assertTrue(
            'Fields: {"fieldName": "TITLE", "fieldType": "STR500"}' in content
        )

    @mock.patch("helpers.write_queries_to_file")
    def test_dump_list_with_table_member_dumps_table_member_information(self, m_write):
        # Given
        query_list = [
            {
                "module_name": "generic.htm",
                "queries": ["$LOOKUP(MODULENAME)$"],
                "MEMBER-TITLE": "John Doe",
                "called_modules": None,
            }
        ]
        # When
        dump_list(query_list, False)
        # Then
        self.assertEqual(m_write.call_args_list[0][0][0], "generic.htm")
        content = m_write.call_args_list[0][0][1]
        self.assertTrue("MEMBER" in content)
        self.assertTrue("TITLE: John Doe" in content)

    def test_print_run_context(self):
        # When
        with mock.patch("builtins.print") as m_print:
            print_run_context("generic.htm", "p", False, False, False)
        # Then
        calls = [
            mock.call("\n"),
            mock.call(100 * "*"),
            mock.call("Will parse the generic.htm module."),
            mock.call("Finding containing modules switch: \x1b[1mOFF\x1b[0m"),
            mock.call("Will find this many modules including itself: \x1b[1m10\x1b[0m"),
            mock.call("Finding tables switch: \x1b[1mOFF\x1b[0m"),
            mock.call("Print queries switch: \x1b[1mON\x1b[0m"),
            mock.call("Print content switch: \x1b[1mOFF\x1b[0m"),
            mock.call(100 * "*"),
            mock.call("\n"),
        ]
        m_print.assert_has_calls(calls)


if __name__ == "__main__":
    unittest_main()
