"""Lambda handler for /transactions and /transactions/{id}."""

import json
from datetime import date
from decimal import Decimal, InvalidOperation

from common import db
from common.auth import user_id_from_event
from common.logger import log_requests
from common.responses import ok, error

COLUMNS = "id, account_id, category_id, amount, description, transaction_date, created_at"

MAX_AMOUNT = Decimal("9999999999.99")


class ValidationError(Exception):
    pass


@log_requests
def handler(event, context):
    try:
        user_id = user_id_from_event(event)
    except (KeyError, TypeError):
        return error("unauthorized", status=401)

    method = event.get("httpMethod")
    raw_id = (event.get("pathParameters") or {}).get("id")
    transaction_id = None
    if raw_id is not None:
        try:
            transaction_id = int(raw_id)
        except ValueError:
            return error("invalid transaction id")

    try:
        if method == "GET":
            return list_transactions(user_id, event.get("queryStringParameters"))
        if method == "POST":
            return create_transaction(user_id, event.get("body"))
        if method == "PUT" and transaction_id is not None:
            return update_transaction(user_id, transaction_id, event.get("body"))
        if method == "DELETE" and transaction_id is not None:
            return delete_transaction(user_id, transaction_id)
    except ValidationError as exc:
        return error(str(exc))

    return error("unsupported route", status=404)


def list_transactions(user_id, query):
    query = query or {}
    where = ["a.user_id = :user_id"]
    params = {"user_id": user_id}

    if "account_id" in query:
        where.append("t.account_id = :account_id")
        params["account_id"] = _parse_int(query["account_id"], "account_id")
    if "category_id" in query:
        where.append("t.category_id = :category_id")
        params["category_id"] = _parse_int(query["category_id"], "category_id")
    if "start_date" in query:
        where.append("t.transaction_date >= :start_date")
        params["start_date"] = _parse_date(query["start_date"], "start_date")
    if "end_date" in query:
        where.append("t.transaction_date <= :end_date")
        params["end_date"] = _parse_date(query["end_date"], "end_date")

    rows = db.execute(
        "SELECT t.id, t.account_id, t.category_id, t.amount, t.description, "
        "t.transaction_date, t.created_at "
        "FROM transactions t JOIN accounts a ON a.id = t.account_id "
        "WHERE " + " AND ".join(where) + " "
        "ORDER BY t.transaction_date DESC, t.id DESC",
        params,
    )
    return ok(rows)


def create_transaction(user_id, body):
    fields = _parse_fields(body)

    # the account and category must both belong to the caller
    rows = db.execute(
        "INSERT INTO transactions "
        "(account_id, category_id, amount, description, transaction_date) "
        "SELECT a.id, c.id, :amount, CAST(:description AS VARCHAR), :transaction_date "
        "FROM accounts a, categories c "
        "WHERE a.id = :account_id AND a.user_id = :user_id "
        "AND c.id = :category_id AND c.user_id = :user_id "
        "RETURNING " + COLUMNS,
        {**fields, "user_id": user_id},
    )
    if not rows:
        return error("account or category not found", status=404)
    return ok(rows[0], status=201)


def update_transaction(user_id, transaction_id, body):
    fields = _parse_fields(body)

    rows = db.execute(
        "UPDATE transactions SET account_id = :account_id, category_id = :category_id, "
        "amount = :amount, description = CAST(:description AS VARCHAR), "
        "transaction_date = :transaction_date "
        "WHERE id = :id "
        "AND account_id IN (SELECT id FROM accounts WHERE user_id = :user_id) "
        "AND EXISTS (SELECT 1 FROM accounts WHERE id = :account_id AND user_id = :user_id) "
        "AND EXISTS (SELECT 1 FROM categories WHERE id = :category_id AND user_id = :user_id) "
        "RETURNING " + COLUMNS,
        {**fields, "id": transaction_id, "user_id": user_id},
    )
    if not rows:
        return error("transaction, account or category not found", status=404)
    return ok(rows[0])


def delete_transaction(user_id, transaction_id):
    rows = db.execute(
        "DELETE FROM transactions WHERE id = :id "
        "AND account_id IN (SELECT id FROM accounts WHERE user_id = :user_id) "
        "RETURNING id",
        {"id": transaction_id, "user_id": user_id},
    )
    if not rows:
        return error("transaction not found", status=404)
    return ok({"id": rows[0]["id"]})


def _parse_fields(body):
    data = _parse_body(body)

    description = data.get("description")
    if description is not None:
        if not isinstance(description, str):
            raise ValidationError("description must be a string")
        description = description.strip() or None
        if description and len(description) > 255:
            raise ValidationError("description must be 255 characters or fewer")

    return {
        "account_id": _parse_int(data.get("account_id"), "account_id"),
        "category_id": _parse_int(data.get("category_id"), "category_id"),
        "amount": _parse_amount(data.get("amount")),
        "description": description,
        "transaction_date": _parse_date(data.get("transaction_date"), "transaction_date"),
    }


def _parse_int(value, name):
    if isinstance(value, bool) or value is None:
        raise ValidationError(f"{name} is required")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be an integer")


def _parse_date(value, name):
    if not value:
        raise ValidationError(f"{name} is required")
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValidationError(f"{name} must be a date in YYYY-MM-DD format")


def _parse_amount(value):
    if isinstance(value, bool) or value is None:
        raise ValidationError("amount is required")
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ValidationError("amount must be a number")
    if not amount.is_finite() or amount == 0:
        raise ValidationError("amount must be a non-zero number")
    if amount.as_tuple().exponent < -2:
        raise ValidationError("amount can have at most 2 decimal places")
    if abs(amount) > MAX_AMOUNT:
        raise ValidationError("amount is too large")
    return amount


def _parse_body(body):
    if not body:
        return {}
    try:
        data = json.loads(body)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
