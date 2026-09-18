"""Thin wrapper around the RDS Data API for parameterized SQL access."""

import os
from datetime import date
from decimal import Decimal

import boto3

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("rds-data")
    return _client


def _to_sql_parameter(name, value):
    if value is None:
        return {"name": name, "value": {"isNull": True}}
    if isinstance(value, bool):
        return {"name": name, "value": {"booleanValue": value}}
    if isinstance(value, int):
        return {"name": name, "value": {"longValue": value}}
    if isinstance(value, float):
        return {"name": name, "value": {"doubleValue": value}}
    if isinstance(value, Decimal):
        return {"name": name, "value": {"stringValue": str(value)}, "typeHint": "DECIMAL"}
    if isinstance(value, date):
        return {"name": name, "value": {"stringValue": value.isoformat()}, "typeHint": "DATE"}
    return {"name": name, "value": {"stringValue": str(value)}}


def _field_value(field):
    if field.get("isNull"):
        return None
    for key in ("stringValue", "longValue", "doubleValue", "booleanValue"):
        if key in field:
            return field[key]
    return None


def _row_to_dict(columns, record):
    return {col: _field_value(field) for col, field in zip(columns, record)}


def execute(sql, params=None):
    """Run a parameterized SQL statement and return rows as a list of dicts.

    `sql` must use named placeholders (e.g. `:user_id`) — never interpolate
    values directly into the query string.
    """
    client = _get_client()
    kwargs = {
        "resourceArn": os.environ["DB_CLUSTER_ARN"],
        "secretArn": os.environ["DB_SECRET_ARN"],
        "database": os.environ["DB_NAME"],
        "sql": sql,
        "includeResultMetadata": True,
    }
    if params:
        kwargs["parameters"] = [_to_sql_parameter(k, v) for k, v in params.items()]

    response = client.execute_statement(**kwargs)
    columns = [meta["name"] for meta in response.get("columnMetadata", [])]
    records = response.get("records", [])
    return [_row_to_dict(columns, record) for record in records]
