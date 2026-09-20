import json
from decimal import Decimal

from budgets import handler as budgets_handler

BUDGET = {"id": 1, "category_id": 2, "monthly_limit": "300.00", "created_at": "2026-01-01"}


def _event(method, path_params=None, body=None):
    return {
        "httpMethod": method,
        "pathParameters": path_params,
        "body": json.dumps(body) if body is not None else None,
    }


def _authed(mocker, user_id=1):
    mocker.patch("budgets.handler.user_id_from_event", return_value=user_id)
    return mocker.patch("budgets.handler.db.execute")


def test_handler_returns_401_when_unauthorized(mocker):
    mocker.patch("budgets.handler.user_id_from_event", side_effect=KeyError)

    response = budgets_handler.handler(_event("GET"), None)

    assert response["statusCode"] == 401


def test_list_budgets_returns_rows(mocker):
    execute = _authed(mocker)
    execute.return_value = [BUDGET]

    response = budgets_handler.handler(_event("GET"), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == [BUDGET]
    assert execute.call_args.args[1] == {"user_id": 1}


def test_create_budget_inserts_row(mocker):
    execute = _authed(mocker)
    execute.return_value = [BUDGET]

    response = budgets_handler.handler(
        _event("POST", body={"category_id": 2, "monthly_limit": 300}), None
    )

    assert response["statusCode"] == 201
    assert json.loads(response["body"]) == BUDGET
    params = execute.call_args.args[1]
    assert params == {"user_id": 1, "category_id": 2, "monthly_limit": Decimal("300")}


def test_create_budget_category_not_found(mocker):
    execute = _authed(mocker)
    execute.side_effect = [[], []]

    response = budgets_handler.handler(
        _event("POST", body={"category_id": 9, "monthly_limit": "50.00"}), None
    )

    assert response["statusCode"] == 404


def test_create_budget_duplicate_returns_409(mocker):
    execute = _authed(mocker)
    execute.side_effect = [[], [{"id": 2}]]

    response = budgets_handler.handler(
        _event("POST", body={"category_id": 2, "monthly_limit": "50.00"}), None
    )

    assert response["statusCode"] == 409


def test_create_budget_requires_category_id(mocker):
    execute = _authed(mocker)

    response = budgets_handler.handler(_event("POST", body={"monthly_limit": 50}), None)

    assert response["statusCode"] == 400
    execute.assert_not_called()


def test_create_budget_rejects_bad_limits(mocker):
    execute = _authed(mocker)

    for bad in (0, -5, "abc", None, True, "10.999", "NaN"):
        response = budgets_handler.handler(
            _event("POST", body={"category_id": 2, "monthly_limit": bad}), None
        )
        assert response["statusCode"] == 400, bad
    execute.assert_not_called()


def test_update_budget_changes_limit(mocker):
    execute = _authed(mocker)
    execute.return_value = [{**BUDGET, "monthly_limit": "450.00"}]

    response = budgets_handler.handler(
        _event("PUT", path_params={"id": "1"}, body={"monthly_limit": "450.00"}), None
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["monthly_limit"] == "450.00"
    assert execute.call_args.args[1]["id"] == 1


def test_update_budget_not_found(mocker):
    execute = _authed(mocker)
    execute.return_value = []

    response = budgets_handler.handler(
        _event("PUT", path_params={"id": "99"}, body={"monthly_limit": 10}), None
    )

    assert response["statusCode"] == 404


def test_update_budget_invalid_id(mocker):
    _authed(mocker)

    response = budgets_handler.handler(
        _event("PUT", path_params={"id": "abc"}, body={"monthly_limit": 10}), None
    )

    assert response["statusCode"] == 400


def test_delete_budget_removes_row(mocker):
    execute = _authed(mocker)
    execute.return_value = [{"id": 3}]

    response = budgets_handler.handler(_event("DELETE", path_params={"id": "3"}), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"id": 3}


def test_delete_budget_not_found(mocker):
    execute = _authed(mocker)
    execute.return_value = []

    response = budgets_handler.handler(_event("DELETE", path_params={"id": "3"}), None)

    assert response["statusCode"] == 404


def test_unsupported_route_returns_404(mocker):
    _authed(mocker)

    response = budgets_handler.handler(_event("PATCH"), None)

    assert response["statusCode"] == 404
