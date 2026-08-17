import pytest

from app.core.sql_guard import SQLGuardError, validate_read_only_sql


def test_adds_limit_and_accepts_allowed_table() -> None:
    guarded = validate_read_only_sql("SELECT * FROM production_orders", {"production_orders"})
    assert guarded.sql.endswith("LIMIT 500")
    assert guarded.tables == ("production_orders",)


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM production_orders",
        "SELECT * FROM hidden_table",
        "SELECT * FROM production_orders; DROP TABLE production_orders",
    ],
)
def test_rejects_unsafe_sql(sql: str) -> None:
    with pytest.raises(SQLGuardError):
        validate_read_only_sql(sql, {"production_orders"})
