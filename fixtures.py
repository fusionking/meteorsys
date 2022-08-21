CONTENT_RESPONSE = {
    "documentPath": "/contentlibrary/modules/generic.htm",
    "content": '<html><a href="$LOOKUP(SOMEVARIABLE)$?$LOOKUP(VARIABLE)$&amp;utm_term=$LOOKUP(MODULE)$"></html>',
}
CONTAINING_MODULE_RESPONSE = {
    "documentPath": "/contentlibrary/modules/containing.htm",
    "content": "<html>$COND(EMPTY(LOOKUP(WISHLIST_COURSES)), NOTHING(),document(contentlibrary/modules, contained.htm))</html>",
}
CONTAINED_MODULE_RESPONSE = {
    "documentPath": "/contentlibrary/modules/contained.htm",
    "content": "<html><body>\n$SETVARS(VARLIST(1, USERS, LOOKUPRECORDS(!MasterData, ALL_USERS, PAIRS(RIID_, LOOKUP(RIID_), ID, LOOKUP(ID)), TITLE)))$</html>",
}

CONTENT_RESPONSES = {
    "generic.htm": CONTENT_RESPONSE,
    "containing.htm": CONTAINING_MODULE_RESPONSE,
    "contained.htm": CONTAINED_MODULE_RESPONSE,
}

TOKEN_EXPIRED_RESPONSE = {
    "type": "",
    "title": "Authentication token expired",
    "errorCode": "TOKEN_EXPIRED",
    "detail": "Token expired",
    "errorDetails": [],
}


TABLE_RESPONSE = {
    "fields": [
        {"fieldName": "TITLE", "fieldType": "STR500"},
        {"fieldName": "ID", "fieldType": "INTEGER"},
    ]
}

TABLE_MEMBERS_RESPONSE = {
    "recordData": {
        "fieldNames": ["TITLE"],
        "records": [["John Doe"]],
        "mapTemplateName": None,
    },
}

LIST_CONTENTS_RESPONSE = {
    "documents": [
        {
            "documentPath": "/contentlibrary/modules/generic.htm",
            "content": None,
        },
        {
            "documentPath": "/contentlibrary/modules/containing.htm",
            "content": None,
        },
    ]
}
