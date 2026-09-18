from datetime import date
from decimal import Decimal

import pytest

from common import db


@pytest.fixture(autouse=True)
def db_env(monkeypatch):
    monkeypatch.setenv("DB_CLUSTER_ARN", "arn:aws:rds:us-east-1:111111111111:cluster:test")
    monkeypatch.setenv("DB_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:111111111111:secret:test")
    monkeypatch.setenv("DB_NAME", "expenses")
    db._client = None
    yield
    db._client = None


def test_execute_sends_expected_request(mocker):
    fake_client = mocker.Mock()
    fake_client.execute_statement.return_value = {
        "columnMetadata": [{"name": "id"}, {"name": "name"}],
        "records": [
            [{"longValue": 1}, {"stringValue": "Groceries"}],
        ],
    }
    mocker.patch("boto3.client", return_value=fake_client)

    rows = db.execute(
        "SELECT id, name FROM categories WHERE user_id = :user_id",
        {"user_id": 7},
    )

    assert rows == [{"id": 1, "name": "Groceries"}]

    fake_client.execute_statement.assert_called_once_with(
        resourceArn="arn:aws:rds:us-east-1:111111111111:cluster:test",
        secretArn="arn:aws:secretsmanager:us-east-1:111111111111:secret:test",
        database="expenses",
        sql="SELECT id, name FROM categories WHERE user_id = :user_id",
        includeResultMetadata=True,
        parameters=[{"name": "user_id", "value": {"longValue": 7}}],
    )


def test_execute_without_params_omits_parameters_key(mocker):
    fake_client = mocker.Mock()
    fake_client.execute_statement.return_value = {"columnMetadata": [], "records": []}
    mocker.patch("boto3.client", return_value=fake_client)

    db.execute("SELECT 1")

    _, kwargs = fake_client.execute_statement.call_args
    assert "parameters" not in kwargs


def test_execute_handles_null_values(mocker):
    fake_client = mocker.Mock()
    fake_client.execute_statement.return_value = {
        "columnMetadata": [{"name": "description"}],
        "records": [[{"isNull": True}]],
    }
    mocker.patch("boto3.client", return_value=fake_client)

    rows = db.execute("SELECT description FROM transactions")

    assert rows == [{"description": None}]


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, {"isNull": True}),
        (True, {"booleanValue": True}),
        (42, {"longValue": 42}),
        (3.14, {"doubleValue": 3.14}),
        ("groceries", {"stringValue": "groceries"}),
    ],
)
def test_to_sql_parameter_basic_types(value, expected):
    param = db._to_sql_parameter("field", value)
    assert param == {"name": "field", "value": expected}


def test_to_sql_parameter_decimal_uses_type_hint():
    param = db._to_sql_parameter("amount", Decimal("19.99"))
    assert param == {
        "name": "amount",
        "value": {"stringValue": "19.99"},
        "typeHint": "DECIMAL",
    }


def test_to_sql_parameter_date_uses_type_hint():
    param = db._to_sql_parameter("transaction_date", date(2026, 1, 15))
    assert param == {
        "name": "transaction_date",
        "value": {"stringValue": "2026-01-15"},
        "typeHint": "DATE",
    }
