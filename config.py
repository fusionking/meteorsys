import os

from decouple import config

# File paths
QUERY_FILE_PATH = "{}/{}".format(
    os.path.dirname(os.path.abspath(__file__)), "modules/QUERIES-{module_name}.notes"
)
SCAN_FILE_PATH = ""

# API credential configuration
USERNAME = config("USERNAME")
PASSWORD = config("PASSWORD")
TOKEN = config("AUTH_TOKEN")

# Keys
RESPONSYS_AUTH_TOKEN_KEY = "responsys_auth_token"
TOKEN_EXPIRATION_SECONDS = 3600

# Responsys URL configuration
LOGIN_URL = config("LOGIN_URL")
CONTENT_URL = config("CONTENT_URL")
TABLE_URL = config("TABLE_URL")
TABLE_MEMBERS_URL = config("TABLE_MEMBERS_URL")
LIST_CONTENTS_URL = config("LIST_CONTENTS_URL")
UPDATE_CONTENT_URL = config("UPDATE_CONTENT_URL")

# Regex Patterns
CONTENT_LIBRARY_REGEX = r"(contentlibrary.*\.htm).*"
QUERY_REGEX = r"(\$.*\))"
TABLE_REGEX = r"(\((?P<folder_name>\!Master[A-Za-z]+),\s?(?P<table_name>[A-Za-z0-9_]+),\s?(?:pairs\()?\s?(?P<qpairs>(?P<qa>[A-Za-z0-9_]+),\s?(\bLOOKUP\(\b)?(?P<qv>[A-Za-z0-9_]+)\)?)+,?\s?(?P<qpairs2>(?P<qa2>[A-Za-z0-9_]+),\s?(\bLOOKUP\(\b)?(?P<qv2>[A-Za-z0-9_]+)\)?)?)"

# Content Words
DOCUMENT_WORD = "document"
DOCUMENTNOBR_WORD = "documentnobr"
CONTENT_LIBRARY_WORD = "contentlibrary"

# Switches
FIND_CONTAINING_MODULES = True
FIND_CONTAINING_MODULES_DEPTH = 10
FIND_TABLES = False
PRINT_QUERIES = True
PRINT_CONTENT = True

# List of folder names to scan
FOLDER_NAMES = [
    "modules",
]

TABLES_TO_QUERIES_DICT = {
    "SOME_TABLE": {
        "fs": "COLUMN_NAME",
        "qav": {"QUERY_COLUMN": "value", "ANOTHER_QUERY_COLUMN": "another_value"},
    }
}
