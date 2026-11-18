"""Error handling: one place that turns a message + status code into an API error."""
from flask import jsonify


class LibraryError(Exception):
    """Raised by services. Services never build HTTP responses themselves."""

    def __init__(self, message, status_code):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def api_error(message, status_code):
    """Create an error with a custom message and HTTP status code. Use: raise api_error("...", 409)."""
    return LibraryError(message, status_code)


def error_response(message, status_code):
    """Build the JSON error response: {"error": message} with the given status code."""
    return jsonify({"error": message}), status_code


# Shortcuts for the three status codes this API uses.
def bad_request(message):
    return api_error(message, 400)


def not_found(message):
    return api_error(message, 404)


def conflict(message):
    return api_error(message, 409)


def register_error_handlers(app):
    @app.errorhandler(LibraryError)
    def handle_library_error(error):
        return error_response(error.message, error.status_code)
