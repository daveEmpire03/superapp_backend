import logging
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {"success": False, "error": response.data}
        request = context.get("request")
        path = request.path if request else "unknown path"
        logger.warning("API [%s] on %s: %s", response.status_code, path, response.data.get("error"))
    return response
