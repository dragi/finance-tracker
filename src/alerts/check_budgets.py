"""Scheduled Lambda: alert when this month's spending passes a category budget."""

import os

import boto3

from common import db
from common.logger import logger

_sns = None


def _get_sns():
    global _sns
    if _sns is None:
        _sns = boto3.client("sns")
    return _sns


def handler(event, context):
    over_budget = find_over_budget()
    for row in over_budget:
        publish_alert(row)
    logger.info("budget check finished", extra={"alerts_sent": len(over_budget)})
    return {"checked": True, "alerts_sent": len(over_budget)}


def find_over_budget():
    return db.execute(
        "SELECT u.email, c.name AS category_name, b.monthly_limit, "
        "SUM(t.amount) AS spent "
        "FROM budgets b "
        "JOIN users u ON u.id = b.user_id "
        "JOIN categories c ON c.id = b.category_id "
        "JOIN accounts a ON a.user_id = b.user_id "
        "JOIN transactions t ON t.account_id = a.id AND t.category_id = b.category_id "
        "WHERE t.transaction_date >= date_trunc('month', CURRENT_DATE) "
        "AND t.transaction_date < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month' "
        "GROUP BY u.email, c.name, b.id, b.monthly_limit "
        "HAVING SUM(t.amount) > b.monthly_limit "
        "ORDER BY u.email, c.name"
    )


def publish_alert(row):
    message = (
        f"{row['email']}: spending on {row['category_name']} is {row['spent']} "
        f"this month, over the budget of {row['monthly_limit']}."
    )
    _get_sns().publish(
        TopicArn=os.environ["SNS_TOPIC_ARN"],
        Subject="budget exceeded",
        Message=message,
    )
