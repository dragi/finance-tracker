from common import auth


def test_get_or_create_user_returns_existing_id(mocker):
    execute = mocker.patch("common.auth.db.execute")
    execute.return_value = [{"id": 5}]

    user_id = auth.get_or_create_user("sub-123", "a@example.com")

    assert user_id == 5
    execute.assert_called_once_with(
        "SELECT id FROM users WHERE cognito_sub = :cognito_sub",
        {"cognito_sub": "sub-123"},
    )


def test_get_or_create_user_creates_when_missing(mocker):
    execute = mocker.patch("common.auth.db.execute")
    execute.side_effect = [[], [{"id": 9}]]

    user_id = auth.get_or_create_user("sub-456", "b@example.com")

    assert user_id == 9
    assert execute.call_count == 2
    insert_sql = execute.call_args_list[1].args[0]
    assert "INSERT INTO users" in insert_sql
    assert "INSERT INTO accounts" in insert_sql


def test_user_id_from_event_extracts_claims(mocker):
    get_or_create = mocker.patch("common.auth.get_or_create_user", return_value=3)
    event = {
        "requestContext": {
            "authorizer": {"claims": {"sub": "sub-789", "email": "c@example.com"}}
        }
    }

    user_id = auth.user_id_from_event(event)

    assert user_id == 3
    get_or_create.assert_called_once_with("sub-789", "c@example.com")
