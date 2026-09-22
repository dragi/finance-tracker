import json

from common.logger import log_requests


def test_log_requests_passes_response_through():
    @log_requests
    def handler(event, context):
        return {"statusCode": 200, "body": "{}"}

    response = handler({"httpMethod": "GET", "resource": "/categories"}, None)

    assert response == {"statusCode": 200, "body": "{}"}


def test_log_requests_turns_exceptions_into_500(caplog):
    @log_requests
    def handler(event, context):
        raise RuntimeError("db is down")

    response = handler({"httpMethod": "GET", "resource": "/categories"}, None)

    assert response["statusCode"] == 500
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    assert json.loads(response["body"]) == {"message": "internal server error"}
    assert "unhandled error" in caplog.text
