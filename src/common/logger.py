"""Shared logger and request logging for the API Lambdas.

Lambda's JSON log format (set in the SAM template) turns these records into
structured CloudWatch entries, including anything passed through `extra`.
"""

import functools
import logging

from common.responses import error

logger = logging.getLogger("expense_tracker")
logger.setLevel(logging.INFO)


def log_requests(func):
    """Log each API request and turn unexpected errors into a 500 response.

    Without this an unhandled exception makes API Gateway return a bare 502
    with no CORS headers, which the browser reports as a confusing CORS error.
    """

    @functools.wraps(func)
    def wrapper(event, context):
        info = {
            "method": event.get("httpMethod"),
            "path": event.get("resource") or event.get("path"),
        }
        try:
            response = func(event, context)
        except Exception:
            logger.exception("unhandled error", extra=info)
            return error("internal server error", status=500)

        logger.info("request handled", extra={**info, "status": response["statusCode"]})
        return response

    return wrapper
