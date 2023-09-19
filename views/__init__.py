from .api import routes as api_routes
from .front import routes as front_routes

routes = (
    *api_routes,
    *front_routes
)
