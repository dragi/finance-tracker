import json

from categories import handler as categories_handler


def _event(method, path_params=None, body=None):
    return {
        "httpMethod": method,
        "pathParameters": path_params,
        "body": json.dumps(body) if body is not None else None,
    }


def test_handler_returns_401_when_unauthorized(mocker):
    mocker.patch("categories.handler.user_id_from_event", side_effect=KeyError)

    response = categories_handler.handler(_event("GET"), None)

    assert response["statusCode"] == 401


def test_list_categories_returns_rows(mocker):
    mocker.patch("categories.handler.user_id_from_event", return_value=1)
    execute = mocker.patch("categories.handler.db.execute")
    execute.return_value = [{"id": 1, "name": "Groceries", "created_at": "2026-01-01"}]

    response = categories_handler.handler(_event("GET"), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == execute.return_value
    execute.assert_called_once_with(
        "SELECT id, name, created_at FROM categories "
        "WHERE user_id = :user_id ORDER BY name",
        {"user_id": 1},
    )


def test_create_category_requires_name(mocker):
    mocker.patch("categories.handler.user_id_from_event", return_value=1)

    response = categories_handler.handler(_event("POST", body={"name": "  "}), None)

    assert response["statusCode"] == 400


def test_create_category_inserts_row(mocker):
    mocker.patch("categories.handler.user_id_from_event", return_value=1)
    execute = mocker.patch("categories.handler.db.execute")
    execute.return_value = [{"id": 2, "name": "Rent", "created_at": "2026-01-02"}]

    response = categories_handler.handler(_event("POST", body={"name": "Rent"}), None)

    assert response["statusCode"] == 201
    assert json.loads(response["body"]) == execute.return_value[0]


def test_update_category_not_found(mocker):
    mocker.patch("categories.handler.user_id_from_event", return_value=1)
    execute = mocker.patch("categories.handler.db.execute")
    execute.return_value = []

    response = categories_handler.handler(
        _event("PUT", path_params={"id": "99"}, body={"name": "New"}), None
    )

    assert response["statusCode"] == 404


def test_update_category_invalid_id(mocker):
    mocker.patch("categories.handler.user_id_from_event", return_value=1)

    response = categories_handler.handler(
        _event("PUT", path_params={"id": "abc"}, body={"name": "New"}), None
    )

    assert response["statusCode"] == 400


def test_delete_category_removes_row(mocker):
    mocker.patch("categories.handler.user_id_from_event", return_value=1)
    execute = mocker.patch("categories.handler.db.execute")
    execute.return_value = [{"id": 3}]

    response = categories_handler.handler(_event("DELETE", path_params={"id": "3"}), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"id": 3}


def test_unsupported_route_returns_404(mocker):
    mocker.patch("categories.handler.user_id_from_event", return_value=1)

    response = categories_handler.handler(_event("PATCH"), None)

    assert response["statusCode"] == 404
