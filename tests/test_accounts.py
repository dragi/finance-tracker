from accounts import handler as accounts_handler


def test_handler_returns_401_when_unauthorized(mocker):
    mocker.patch("accounts.handler.user_id_from_event", side_effect=KeyError)

    response = accounts_handler.handler({"httpMethod": "GET"}, None)

    assert response["statusCode"] == 401


def test_list_accounts_returns_rows(mocker):
    mocker.patch("accounts.handler.user_id_from_event", return_value=1)
    execute = mocker.patch("accounts.handler.db.execute")
    execute.return_value = [{"id": 4, "name": "Main", "created_at": "2026-01-01"}]

    response = accounts_handler.handler({"httpMethod": "GET"}, None)

    assert response["statusCode"] == 200
    execute.assert_called_once_with(
        "SELECT id, name, created_at FROM accounts "
        "WHERE user_id = :user_id ORDER BY id",
        {"user_id": 1},
    )


def test_unsupported_method_returns_404(mocker):
    mocker.patch("accounts.handler.user_id_from_event", return_value=1)

    response = accounts_handler.handler({"httpMethod": "POST"}, None)

    assert response["statusCode"] == 404
