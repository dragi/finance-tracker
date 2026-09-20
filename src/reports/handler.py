"""Lambda handler for /reports/monthly."""

from common import db
from common.auth import user_id_from_event
from common.responses import ok, error


class ValidationError(Exception):
    pass


def handler(event, context):
    try:
        user_id = user_id_from_event(event)
    except (KeyError, TypeError):
        return error("unauthorized", status=401)

    if event.get("httpMethod") != "GET":
        return error("unsupported route", status=404)

    try:
        return monthly_report(user_id, event.get("queryStringParameters"))
    except ValidationError as exc:
        return error(str(exc))


def monthly_report(user_id, query):
    query = query or {}
    where = ["a.user_id = :user_id"]
    params = {"user_id": user_id}

    if "year" in query:
        where.append("EXTRACT(YEAR FROM t.transaction_date) = :year")
        params["year"] = _parse_year(query["year"])
    if "category_id" in query:
        where.append("t.category_id = :category_id")
        params["category_id"] = _parse_int(query["category_id"], "category_id")

    rows = db.execute(
        "SELECT c.id AS category_id, c.name AS category_name, "
        "to_char(t.transaction_date, 'YYYY-MM') AS month, "
        "SUM(t.amount) AS total, COUNT(*) AS transaction_count "
        "FROM transactions t "
        "JOIN accounts a ON a.id = t.account_id "
        "JOIN categories c ON c.id = t.category_id "
        "WHERE " + " AND ".join(where) + " "
        "GROUP BY c.id, c.name, month "
        "ORDER BY month DESC, c.name",
        params,
    )
    return ok(rows)


def _parse_int(value, name):
    if isinstance(value, bool) or value is None:
        raise ValidationError(f"{name} is required")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be an integer")


def _parse_year(value):
    try:
        year = int(value)
    except (TypeError, ValueError):
        raise ValidationError("year must be an integer")
    if year < 1970 or year > 9999:
        raise ValidationError("year must be a valid 4-digit year")
    return year
