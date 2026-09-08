import re
import sqlparse

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "ATTACH", "COPY", "PRAGMA", "EXPORT", "IMPORT",
]


def is_select_only(sql):
    parsed = sqlparse.parse(sql)
    if not parsed:
        return False, "could not parse sql"

    statement_type = parsed[0].get_type()
    if statement_type != "SELECT":
        return False, f"only SELECT statements are allowed, got {statement_type}"

    upper_sql = sql.upper()
    for word in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{word}\b", upper_sql):
            return False, f"query contains a forbidden keyword: {word}"

    return True, None


def check_tables_exist(sql, known_tables):
    upper_sql = sql.upper()
    referenced = re.findall(r"(?:FROM|JOIN)\s+\"?(\w+)\"?", upper_sql)
    known_upper = [t.upper() for t in known_tables]

    unknown = [t for t in referenced if t not in known_upper]
    if unknown:
        return False, f"query references unknown table(s): {', '.join(unknown)}"

    return True, None


def check_qualified_columns(sql, known_columns):
    qualified = re.findall(r"\b(\w+)\.(\w+)\b", sql)
    known_set = {(t.lower(), c.lower()) for t, c in known_columns}

    for table, column in qualified:
        if (table.lower(), column.lower()) not in known_set:
            return False, f"unknown column reference: {table}.{column}"

    return True, None


def validator_node(state, known_columns):
    sql = state["generated_sql"]

    ok, error = is_select_only(sql)
    if not ok:
        return {**state, "is_valid_sql": False, "validation_error": error}

    ok, error = check_tables_exist(sql, state["tables"])
    if not ok:
        return {**state, "is_valid_sql": False, "validation_error": error}

    ok, error = check_qualified_columns(sql, known_columns)
    if not ok:
        return {**state, "is_valid_sql": False, "validation_error": error}

    return {**state, "is_valid_sql": True, "validation_error": None}