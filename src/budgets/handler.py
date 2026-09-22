"""Lambda handler for /budgets and /budgets/{id}."""

import json
from decimal import Decimal, InvalidOperation

from common import db
from common.auth import user_id_from_event
from common.logger import log_requests
from common.responses import ok, error

COLUMNS = "id, category_id, monthly_limit, created_at"

MAX_LIMIT = Decimal("9999999999.99")


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
    budget_id = None
    if raw_id is not None:
        try:
            budget_id = int(raw_id)
        except ValueError:
            return error("invalid budget id")

    try:
        if method == "GET":
            return list_budgets(user_id)
        if method == "POST":
            return create_budget(user_id, event.get("body"))
        if method == "PUT" and budget_id is not None:
            return update_budget(user_id, budget_id, event.get("body"))
        if method == "DELETE" and budget_id is not None:
            return delete_budget(user_id, budget_id)
    except ValidationError as exc:
        return error(str(exc))

    return error("unsupported route", status=404)


def list_budgets(user_id):
    rows = db.execute(
        "SELECT " + COLUMNS + " FROM budgets "
        "WHERE user_id = :user_id ORDER BY category_id",
        {"user_id": user_id},
    )
    return ok(rows)


def create_budget(user_id, body):
    data = _parse_body(body)
    category_id = _parse_int(data.get("category_id"), "category_id")
    monthly_limit = _parse_limit(data.get("monthly_limit"))

    # the category must belong to the caller, and only one budget per category
    rows = db.execute(
        "INSERT INTO budgets (user_id, category_id, monthly_limit) "
        "SELECT :user_id, c.id, :monthly_limit FROM categories c "
        "WHERE c.id = :category_id AND c.user_id = :user_id "
        "ON CONFLICT (user_id, category_id) DO NOTHING "
        "RETURNING " + COLUMNS,
        {"user_id": user_id, "category_id": category_id, "monthly_limit": monthly_limit},
    )
    if rows:
        return ok(rows[0], status=201)

    exists = db.execute(
        "SELECT id FROM categories WHERE id = :category_id AND user_id = :user_id",
        {"category_id": category_id, "user_id": user_id},
    )
    if not exists:
        return error("category not found", status=404)
    return error("a budget for this category already exists", status=409)


def update_budget(user_id, budget_id, body):
    monthly_limit = _parse_limit(_parse_body(body).get("monthly_limit"))

    rows = db.execute(
        "UPDATE budgets SET monthly_limit = :monthly_limit "
        "WHERE id = :id AND user_id = :user_id "
        "RETURNING " + COLUMNS,
        {"id": budget_id, "user_id": user_id, "monthly_limit": monthly_limit},
    )
    if not rows:
        return error("budget not found", status=404)
    return ok(rows[0])


def delete_budget(user_id, budget_id):
    rows = db.execute(
        "DELETE FROM budgets WHERE id = :id AND user_id = :user_id RETURNING id",
        {"id": budget_id, "user_id": user_id},
    )
    if not rows:
        return error("budget not found", status=404)
    return ok({"id": rows[0]["id"]})


def _parse_int(value, name):
    if isinstance(value, bool) or value is None:
        raise ValidationError(f"{name} is required")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be an integer")


def _parse_limit(value):
    if isinstance(value, bool) or value is None:
        raise ValidationError("monthly_limit is required")
    try:
        limit = Decimal(str(value))
    except InvalidOperation:
        raise ValidationError("monthly_limit must be a number")
    if not limit.is_finite() or limit <= 0:
        raise ValidationError("monthly_limit must be greater than zero")
    if limit.as_tuple().exponent < -2:
        raise ValidationError("monthly_limit can have at most 2 decimal places")
    if limit > MAX_LIMIT:
        raise ValidationError("monthly_limit is too large")
    return limit


def _parse_body(body):
    if not body:
        return {}
    try:
        data = json.loads(body)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
