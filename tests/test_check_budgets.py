from alerts import check_budgets

ROW = {
    "email": "test@example.com",
    "category_name": "Groceries",
    "monthly_limit": "300.00",
    "spent": "342.10",
}


def test_find_over_budget_scopes_to_current_month(mocker):
    execute = mocker.patch("alerts.check_budgets.db.execute", return_value=[ROW])

    rows = check_budgets.find_over_budget()

    assert rows == [ROW]
    sql = execute.call_args.args[0]
    assert "date_trunc('month', CURRENT_DATE)" in sql
    assert "HAVING SUM(t.amount) > b.monthly_limit" in sql


def test_handler_publishes_one_alert_per_over_budget_row(mocker, monkeypatch):
    monkeypatch.setenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123:budget-alerts")
    other = {**ROW, "category_name": "Rent", "spent": "1500.00", "monthly_limit": "1200.00"}
    mocker.patch("alerts.check_budgets.db.execute", return_value=[ROW, other])
    sns = mocker.patch("alerts.check_budgets._get_sns").return_value

    result = check_budgets.handler({}, None)

    assert result == {"checked": True, "alerts_sent": 2}
    assert sns.publish.call_count == 2
    kwargs = sns.publish.call_args_list[0].kwargs
    assert kwargs["TopicArn"] == "arn:aws:sns:us-east-1:123:budget-alerts"
    assert "Groceries" in kwargs["Message"]
    assert "342.10" in kwargs["Message"]
    assert "300.00" in kwargs["Message"]


def test_handler_sends_nothing_when_within_budget(mocker):
    mocker.patch("alerts.check_budgets.db.execute", return_value=[])
    sns = mocker.patch("alerts.check_budgets._get_sns").return_value

    result = check_budgets.handler({}, None)

    assert result == {"checked": True, "alerts_sent": 0}
    sns.publish.assert_not_called()
