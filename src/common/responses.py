"""API Gateway proxy-integration response helpers."""

import json
from decimal import Decimal


class _JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, cls=_JSONEncoder),
    }


def ok(data, status=200):
    return _response(status, data)


def error(message, status=400):
    return _response(status, {"message": message})
