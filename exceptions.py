from http import HTTPStatus


class HandledException(Exception):

    def __init__(self,
                 error_message=None,
                 error_status=None):
        super().__init__(error_message or self.error_message)
        self.error_status = error_status or self.error_status


class ServiceException(HandledException):
    error_message = HTTPStatus.BAD_REQUEST.name
    error_status = HTTPStatus.BAD_REQUEST.value


class AuthenticationException(HandledException):
    error_message = HTTPStatus.UNAUTHORIZED.name
    error_status = HTTPStatus.UNAUTHORIZED.value


class AuthorizationException(HandledException):
    error_message = HTTPStatus.FORBIDDEN.name
    error_status = HTTPStatus.FORBIDDEN.value


class MethodNotAllowedException(HandledException):
    error_message = "Method Not Allowed"
    error_status = HTTPStatus.METHOD_NOT_ALLOWED.value
