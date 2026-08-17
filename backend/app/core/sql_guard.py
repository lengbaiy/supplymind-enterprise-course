import re
from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError


class SQLGuardError(ValueError):
    pass


@dataclass(frozen=True)
class GuardedSQL:
    sql: str
    tables: tuple[str, ...]


FORBIDDEN_FUNCTIONS = {"pg_sleep", "load_file", "sleep", "benchmark"}


def validate_read_only_sql(sql: str, allowed_tables: set[str], max_rows: int = 500) -> GuardedSQL:
    if not sql or len(sql) > 20_000:
        raise SQLGuardError("SQL is empty or exceeds the maximum length")
    if ";" in sql.rstrip("; ").strip():
        raise SQLGuardError("Only one SQL statement is allowed")
    try:
        statements = parse(sql)
    except ParseError as exc:
        raise SQLGuardError("SQL cannot be parsed") from exc
    if len(statements) != 1 or not isinstance(statements[0], exp.Query):
        raise SQLGuardError("Only SELECT or WITH queries are allowed")
    statement = statements[0]
    if statement.find(exp.Insert) or statement.find(exp.Update) or statement.find(exp.Delete):
        raise SQLGuardError("Write operations are forbidden")
    tables = tuple(sorted({table.name for table in statement.find_all(exp.Table)}))
    if not tables:
        raise SQLGuardError("Query must reference an approved table")
    unknown = set(tables) - allowed_tables
    if unknown:
        raise SQLGuardError(f"Table is not approved: {', '.join(sorted(unknown))}")
    functions = {function.name.lower() for function in statement.find_all(exp.Anonymous)}
    if functions & FORBIDDEN_FUNCTIONS:
        raise SQLGuardError("Query uses a forbidden function")
    if not re.search(r"\blimit\s+\d+", sql, re.IGNORECASE):
        sql = f"{sql.rstrip(';')} LIMIT {max_rows}"
    return GuardedSQL(sql=sql, tables=tables)
