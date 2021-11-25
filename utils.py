import os
import logging
import datetime
from http import HTTPStatus
from urllib.parse import urljoin

from aiohttp import web

import config
from constants import ControllerResult, BSVariant
from responses import ControllerResponse


def setup_routes(app, routes):
    """Sets up application routes."""
    app.router.add_static("/static/",
                          path=os.path.join(config.DIRS["BASE_DIR"], "static"),
                          name="static")
    for route in routes:
        app.router.add_route(**route)


def setup_middlewares(app, middlewares):
    """Sets up application middlewares."""
    [app.middlewares.append(mw) for mw in middlewares]


async def get_request_data(request, secret_fields=[]):
    """Gets request data, hides secret fields for logging."""
    request_data = {}
    if request.method == "GET":
        request_data = dict(request.query)
    else:
        request_data = dict(await request.post())
        if not request_data and await request.text():
            request_data = dict(await request.json())
    log_data = dict(request_data)
    for k in secret_fields:
        log_data.pop(k, None)
    headers = dict(request.headers.items()) if request.headers else {}
    return dict(data=request_data, ip=request.remote,
                url=request.url, method=request.method,
                headers=headers, log_data=log_data)


def get_log(path, level, formatter, logger_name):
    """Gets file logger."""
    fh = logging.FileHandler(path)
    fh.setLevel(level)
    fh.setFormatter(formatter)
    log = logging.getLogger(logger_name)
    if log.hasHandlers():
        log.handlers.clear()
    log.addHandler(fh)
    log.setLevel(fh.level)
    return log


async def init_app(app):
    # Connect to db connection pool
    if not app["apscron_db"].is_connected:
        await app["apscron_db"].connect()
    # Start scheduler
    app["apscheduler"].start()
    app["app_log"].debug("APScron started")


async def close_app(app):
    # Close db connection pool
    if app["apscron_db"].is_connected:
        await app["apscron_db"].close()
    # Shutdown scheduler
    app["apscheduler"].shutdown()
    app["app_log"].debug("APScron stopped")


def setup_template_functions(jinja_env):
    """Sets up global template functions."""
    template_function_map = {"static": get_static}
    for k, v in template_function_map.items():
        jinja_env.globals[k] = v


def flash(request, message, variant, title):
    """Manages messages and its display options."""
    if request.get("messages"):
        request["messages"].append(
            {"message": message, "variant": variant, "title": title})
    else:
        request["messages"] = [
            {"message": message, "variant": variant, "title": title}]


def convert_types(obj, datetime_format="%Y-%m-%d %H:%M:%S"):
    """Specifies how to convert python types to json string."""
    if isinstance(obj, datetime.datetime):
        return obj.strftime(datetime_format)
    else:
        return str(obj)


def get_static(path):
    """Gets static assets path."""
    path = path or ''
    return urljoin(config.STATIC_PATH_URL, path) if path else ''


async def get_error_response(error, status=HTTPStatus.BAD_REQUEST):
    """Gets aiohttp json error response."""
    if isinstance(error, type):
        return web.json_response(
            ControllerResponse(ControllerResult.Failure,
                               messages=[{"message": error.error_message,
                                          "variant": BSVariant.Danger.name,
                                          "title": BSVariant.Danger.title}]),
            status=error.error_status)
    else:
        return web.json_response(
            ControllerResponse(ControllerResult.Failure,
                               messages=[{"message": str(error),
                                          "variant": BSVariant.Danger.name,
                                          "title": BSVariant.Danger.title}]),
            status=status)


def get_token(request):
    """Gets auth token from request headers."""
    token = None
    token_header = request.headers.get(config.DEFAULT_AUTH_HEADER)
    if token_header:
        token = token_header.split(" ")[-1]
    return token


def set_session_user(session, user):
    """Sets user data required for front-end rendering."""
    user = dict(user.__data__)
    user_data = {}
    for k, v in user.items():
        if k in ["id", "username", "permissions", "is_admin", "is_active"]:
            user_data[k] = v
    session["user"] = user_data
    return user_data
