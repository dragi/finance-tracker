import json
from datetime import date
from decimal import Decimal

from transactions import handler as transactions_handler

VALID_BODY = {
    "account_id": 1,
    "category_id": 2,
    "amount": "12.50",
    "description": "lunch",
    "transaction_date": "2026-03-04",
}

ROW = {
    "id": 7,
    "account_id": 1,
    "category_id": 2,
    "amount": "12.50",
    "description": "lunch",
    "transaction_date": "2026-03-04",
    "created_at": "2026-03-04 10:00:00",
}


def _event(method, path_params=None, body=None, query=None):
    return {
        "httpMethod": method,
        "pathParameters": path_params,
        "queryStringParameters": query,
        "body": json.dumps(body) if body is not None else None,
    }


def _authed(mocker, user_id=1):
    mocker.patch("transactions.handler.user_id_from_event", return_value=user_id)
    return mocker.patch("transactions.handler.db.execute")


def test_handler_returns_401_when_unauthorized(mocker):
    mocker.patch("transactions.handler.user_id_from_event", side_effect=KeyError)

    response = transactions_handler.handler(_event("GET"), None)

    assert response["statusCode"] == 401


def test_list_transactions_without_filters(mocker):
    execute = _authed(mocker)
    execute.return_value = [ROW]

    response = transactions_handler.handler(_event("GET"), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == [ROW]
    sql, params = execute.call_args.args
    assert "a.user_id = :user_id" in sql
    assert params == {"user_id": 1}


def test_list_transactions_applies_all_filters(mocker):
    execute = _authed(mocker)
    execute.return_value = []
    query = {
        "account_id": "1",
        "category_id": "2",
        "start_date": "2026-03-01",
        "end_date": "2026-03-31",
    }

    response = transactions_handler.handler(_event("GET", query=query), None)

    assert response["statusCode"] == 200
    sql, params = execute.call_args.args
    assert "t.account_id = :account_id" in sql
    assert "t.category_id = :category_id" in sql
    assert "t.transaction_date >= :start_date" in sql
    assert "t.transaction_date <= :end_date" in sql
    assert params == {
        "user_id": 1,
        "account_id": 1,
        "category_id": 2,
        "start_date": date(2026, 3, 1),
        "end_date": date(2026, 3, 31),
    }


def test_list_transactions_never_interpolates_filter_values(mocker):
    execute = _authed(mocker)
    execute.return_value = []
    query = {"account_id": "1; DROP TABLE transactions"}

    response = transactions_handler.handler(_event("GET", query=query), None)

    assert response["statusCode"] == 400
    execute.assert_not_called()


def test_list_transactions_rejects_bad_date(mocker):
    execute = _authed(mocker)

    response = transactions_handler.handler(
        _event("GET", query={"start_date": "03/01/2026"}), None
    )

    assert response["statusCode"] == 400
    execute.assert_not_called()


def test_create_transaction_inserts_row(mocker):
    execute = _authed(mocker)
    execute.return_value = [ROW]

    response = transactions_handler.handler(_event("POST", body=VALID_BODY), None)

    assert response["statusCode"] == 201
    assert json.loads(response["body"]) == ROW
    params = execute.call_args.args[1]
    assert params["amount"] == Decimal("12.50")
    assert params["transaction_date"] == date(2026, 3, 4)
    assert params["user_id"] == 1


def test_create_transaction_404_when_account_or_category_not_owned(mocker):
    execute = _authed(mocker)
    execute.return_value = []

    response = transactions_handler.handler(_event("POST", body=VALID_BODY), None)

    assert response["statusCode"] == 404


def test_create_transaction_blank_description_stored_as_null(mocker):
    execute = _authed(mocker)
    execute.return_value = [ROW]
    body = {**VALID_BODY, "description": "   "}

    transactions_handler.handler(_event("POST", body=body), None)

    assert execute.call_args.args[1]["description"] is None


def test_create_transaction_rejects_invalid_input(mocker):
    execute = _authed(mocker)
    bad_bodies = [
        {**VALID_BODY, "amount": "abc"},
        {**VALID_BODY, "amount": "0"},
        {**VALID_BODY, "amount": "1.234"},
        {**VALID_BODY, "amount": "NaN"},
        {**VALID_BODY, "amount": True},
        {**VALID_BODY, "amount": "99999999999"},
        {**VALID_BODY, "transaction_date": "not-a-date"},
        {**VALID_BODY, "description": "x" * 256},
        {**VALID_BODY, "description": 5},
        {k: v for k, v in VALID_BODY.items() if k != "account_id"},
        {k: v for k, v in VALID_BODY.items() if k != "category_id"},
        {k: v for k, v in VALID_BODY.items() if k != "amount"},
        {k: v for k, v in VALID_BODY.items() if k != "transaction_date"},
    ]

    for body in bad_bodies:
        response = transactions_handler.handler(_event("POST", body=body), None)
        assert response["statusCode"] == 400, body

    execute.assert_not_called()


def test_create_transaction_accepts_negative_amount(mocker):
    execute = _authed(mocker)
    execute.return_value = [ROW]
    body = {**VALID_BODY, "amount": -20}

    response = transactions_handler.handler(_event("POST", body=body), None)

    assert response["statusCode"] == 201
    assert execute.call_args.args[1]["amount"] == Decimal("-20")


def test_create_transaction_with_empty_body_is_400(mocker):
    execute = _authed(mocker)

    response = transactions_handler.handler(_event("POST"), None)

    assert response["statusCode"] == 400
    execute.assert_not_called()


def test_update_transaction_returns_updated_row(mocker):
    execute = _authed(mocker)
    execute.return_value = [ROW]

    response = transactions_handler.handler(
        _event("PUT", path_params={"id": "7"}, body=VALID_BODY), None
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == ROW
    params = execute.call_args.args[1]
    assert params["id"] == 7
    assert params["user_id"] == 1


def test_update_transaction_not_found(mocker):
    execute = _authed(mocker)
    execute.return_value = []

    response = transactions_handler.handler(
        _event("PUT", path_params={"id": "99"}, body=VALID_BODY), None
    )

    assert response["statusCode"] == 404


def test_update_transaction_invalid_id(mocker):
    execute = _authed(mocker)

    response = transactions_handler.handler(
        _event("PUT", path_params={"id": "abc"}, body=VALID_BODY), None
    )

    assert response["statusCode"] == 400
    execute.assert_not_called()


def test_update_transaction_requires_valid_body(mocker):
    execute = _authed(mocker)

    response = transactions_handler.handler(
        _event("PUT", path_params={"id": "7"}, body={"amount": "5"}), None
    )

    assert response["statusCode"] == 400
    execute.assert_not_called()


def test_delete_transaction_removes_row(mocker):
    execute = _authed(mocker)
    execute.return_value = [{"id": 7}]

    response = transactions_handler.handler(
        _event("DELETE", path_params={"id": "7"}), None
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"id": 7}
    assert execute.call_args.args[1] == {"id": 7, "user_id": 1}


def test_delete_transaction_not_found(mocker):
    execute = _authed(mocker)
    execute.return_value = []

    response = transactions_handler.handler(
        _event("DELETE", path_params={"id": "99"}), None
    )

    assert response["statusCode"] == 404


def test_put_and_delete_without_id_are_404(mocker):
    _authed(mocker)

    for method in ("PUT", "DELETE"):
        response = transactions_handler.handler(_event(method, body=VALID_BODY), None)
        assert response["statusCode"] == 404


def test_unsupported_route_returns_404(mocker):
    _authed(mocker)

    response = transactions_handler.handler(_event("PATCH"), None)

    assert response["statusCode"] == 404
