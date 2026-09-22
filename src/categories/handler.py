"""Lambda handler for /categories and /categories/{id}."""

import json

from common import db
from common.auth import user_id_from_event
from common.logger import log_requests
from common.responses import ok, error


@log_requests
def handler(event, context):
    try:
        user_id = user_id_from_event(event)
    except (KeyError, TypeError):
        return error("unauthorized", status=401)

    method = event.get("httpMethod")
    raw_id = (event.get("pathParameters") or {}).get("id")
    category_id = None
    if raw_id is not None:
        try:
            category_id = int(raw_id)
        except ValueError:
            return error("invalid category id")

    if method == "GET":
        return list_categories(user_id)
    if method == "POST":
        return create_category(user_id, event.get("body"))
    if method == "PUT" and category_id is not None:
        return update_category(user_id, category_id, event.get("body"))
    if method == "DELETE" and category_id is not None:
        return delete_category(user_id, category_id)

    return error("unsupported route", status=404)


def list_categories(user_id):
    rows = db.execute(
        "SELECT id, name, created_at FROM categories "
        "WHERE user_id = :user_id ORDER BY name",
        {"user_id": user_id},
    )
    return ok(rows)


def create_category(user_id, body):
    name = _parse_body(body).get("name", "").strip()
    if not name:
        return error("name is required")

    rows = db.execute(
        "INSERT INTO categories (user_id, name) VALUES (:user_id, :name) "
        "RETURNING id, name, created_at",
        {"user_id": user_id, "name": name},
    )
    return ok(rows[0], status=201)


def update_category(user_id, category_id, body):
    name = _parse_body(body).get("name", "").strip()
    if not name:
        return error("name is required")

    rows = db.execute(
        "UPDATE categories SET name = :name "
        "WHERE id = :id AND user_id = :user_id "
        "RETURNING id, name, created_at",
        {"id": category_id, "user_id": user_id, "name": name},
    )
    if not rows:
        return error("category not found", status=404)
    return ok(rows[0])


def delete_category(user_id, category_id):
    rows = db.execute(
        "DELETE FROM categories WHERE id = :id AND user_id = :user_id RETURNING id",
        {"id": category_id, "user_id": user_id},
    )
    if not rows:
        return error("category not found", status=404)
    return ok({"id": rows[0]["id"]})


def _parse_body(body):
    if not body:
        return {}
    try:
        return json.loads(body) or {}
    except (TypeError, ValueError):
        return {}
