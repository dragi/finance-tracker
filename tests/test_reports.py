import json

from reports import handler as reports_handler

ROW = {
    "category_id": 2,
    "category_name": "Groceries",
    "month": "2026-03",
    "total": "125.50",
    "transaction_count": 4,
}


def _event(method="GET", query=None):
    return {"httpMethod": method, "queryStringParameters": query}


def _authed(mocker, user_id=1):
    mocker.patch("reports.handler.user_id_from_event", return_value=user_id)
    return mocker.patch("reports.handler.db.execute")


def test_handler_returns_401_when_unauthorized(mocker):
    mocker.patch("reports.handler.user_id_from_event", side_effect=KeyError)

    response = reports_handler.handler(_event(), None)

    assert response["statusCode"] == 401


def test_monthly_report_without_filters(mocker):
    execute = _authed(mocker)
    execute.return_value = [ROW]

    response = reports_handler.handler(_event(), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == [ROW]
    sql, params = execute.call_args.args
    assert "a.user_id = :user_id" in sql
    assert "GROUP BY c.id, c.name, month" in sql
    assert params == {"user_id": 1}


def test_monthly_report_filters_by_year(mocker):
    execute = _authed(mocker)
    execute.return_value = []

    response = reports_handler.handler(_event(query={"year": "2026"}), None)

    assert response["statusCode"] == 200
    sql, params = execute.call_args.args
    assert "EXTRACT(YEAR FROM t.transaction_date) = :year" in sql
    assert params == {"user_id": 1, "year": 2026}


def test_monthly_report_filters_by_category(mocker):
    execute = _authed(mocker)
    execute.return_value = []

    response = reports_handler.handler(_event(query={"category_id": "5"}), None)

    assert response["statusCode"] == 200
    sql, params = execute.call_args.args
    assert "t.category_id = :category_id" in sql
    assert params == {"user_id": 1, "category_id": 5}


def test_monthly_report_rejects_bad_year(mocker):
    execute = _authed(mocker)

    response = reports_handler.handler(_event(query={"year": "abc"}), None)

    assert response["statusCode"] == 400
    execute.assert_not_called()


def test_monthly_report_rejects_bad_category_id(mocker):
    execute = _authed(mocker)

    response = reports_handler.handler(_event(query={"category_id": "abc"}), None)

    assert response["statusCode"] == 400
    execute.assert_not_called()


def test_unsupported_method_returns_404(mocker):
    _authed(mocker)

    response = reports_handler.handler(_event(method="POST"), None)

    assert response["statusCode"] == 404
