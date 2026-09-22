"""Lambda handler for /accounts (read-only - accounts are created with the user)."""

from common import db
from common.auth import user_id_from_event
from common.responses import ok, error


def handler(event, context):
    try:
        user_id = user_id_from_event(event)
    except (KeyError, TypeError):
        return error("unauthorized", status=401)

    if event.get("httpMethod") == "GET":
        return list_accounts(user_id)

    return error("unsupported route", status=404)


def list_accounts(user_id):
    rows = db.execute(
        "SELECT id, name, created_at FROM accounts "
        "WHERE user_id = :user_id ORDER BY id",
        {"user_id": user_id},
    )
    return ok(rows)
