from http import HTTPStatus

from aiohttp import web
from aiohttp.web_response import StreamResponse
from aiohttp.web_exceptions import HTTPException, HTTPRedirection

from controllers import ControllerResponse
from utils import get_error_response


@web.middleware
async def request_middleware(request, handler):
    # Return static requests without logging whatsoever
    if request.path.startswith("/static/"):
        return await handler(request)
    if request.path.startswith("/favicon"):
        raise web.HTTPFound('/static/img/favicon.svg')
    # When aiohttp does not know where to route the request,
    # including due to wrong method
    if handler.__name__ == "_handle":
        try:
            response = await handler(request)
            return response
        except HTTPException as e:
            return await get_error_response(
                str(e), e.status_code)

    try:
        if not request.app["apscron_db"].is_connected:
            await request.app["apscron_db"].connect()

        response = await handler(request)
        if isinstance(response, HTTPRedirection):
            raise response
        elif isinstance(response, StreamResponse):
            return response
        elif isinstance(response, ControllerResponse):
            if response.overrides.get("text"):
                return web.json_response(**response.overrides)
            messages = request.pop("messages", None)
            if messages:
                response["messages"] = messages
            return web.json_response(response, **response.overrides)
        else:
            return await get_error_response(
                "Failed to process request", HTTPStatus.INTERNAL_SERVER_ERROR)

    except HTTPException as e:
        return await get_error_response(str(e), e.status_code)

middlewares = [request_middleware]
