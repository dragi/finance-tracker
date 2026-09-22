"""Resolves the app's internal user row from a Cognito-authenticated request."""

from common import db


def get_or_create_user(cognito_sub, email):
    rows = db.execute(
        "SELECT id FROM users WHERE cognito_sub = :cognito_sub",
        {"cognito_sub": cognito_sub},
    )
    if rows:
        return rows[0]["id"]

    # new users get a default account in the same statement so they can
    # start adding transactions right away
    rows = db.execute(
        "WITH new_user AS ("
        "INSERT INTO users (cognito_sub, email) VALUES (:cognito_sub, :email) "
        "RETURNING id), "
        "new_account AS ("
        "INSERT INTO accounts (user_id, name) SELECT id, 'Main' FROM new_user) "
        "SELECT id FROM new_user",
        {"cognito_sub": cognito_sub, "email": email},
    )
    return rows[0]["id"]


def user_id_from_event(event):
    claims = event["requestContext"]["authorizer"]["claims"]
    return get_or_create_user(claims["sub"], claims.get("email", ""))
