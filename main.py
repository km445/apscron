import os
import base64

import jinja2
import aiohttp_jinja2
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor
# from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from cryptography import fernet
from aiohttp import web
from aiohttp_session import setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from pytz import utc

import config
from views import routes
from utils import (setup_routes, setup_middlewares, get_log, init_app,
                   close_app, setup_template_functions)
from middlewares import middlewares
from jobstores.peewee_jobstore import PeeweeJobStore
from models import async_db_manager


# Create logs folder
if not os.path.exists(config.DIRS["LOG_TO"]):
    os.makedirs(config.DIRS["LOG_TO"])

# Get WSGI application and set up logging
app = web.Application()
app_log = get_log(
    os.path.join(config.DIRS["LOG_TO"], config.LOGGER["file"]),
    config.LOGGER["level"], config.LOGGER["formatter"], "apscron")
peewee_log = get_log(
    os.path.join(config.DIRS["LOG_TO"], config.LOGGER["peewee_file"]),
    config.LOGGER["level"], config.LOGGER["formatter"], "peewee")
aps_log = get_log(
    os.path.join(config.DIRS["LOG_TO"], config.LOGGER["apscron_file"]),
    config.LOGGER["level"], config.LOGGER["formatter"], "apscheduler")

# Setup encrypted cookie session
fernet_key = fernet.Fernet.generate_key()
secret_key = base64.urlsafe_b64decode(fernet_key)
setup(app, EncryptedCookieStorage(
    secret_key, cookie_name=config.COOKIE_NAME, max_age=config.MAX_AGE))

# Setup template environment and functions
jinja_env = aiohttp_jinja2.setup(
    app,
    loader=jinja2.FileSystemLoader(config.DIRS["TEMPLATE_DIR"]),
    context_processors=[aiohttp_jinja2.request_processor])

setup_template_functions(jinja_env)

jobstores = {
    "default": PeeweeJobStore()
}
executors = {
    "default": AsyncIOExecutor()
}
# executors = {
#     "default": ThreadPoolExecutor(20),
#     "processpool": ProcessPoolExecutor(5)
# }
job_defaults = {
    "coalesce": True,
}
scheduler = AsyncIOScheduler(jobstores=jobstores, executors=executors,
                             job_defaults=job_defaults, timezone=utc)

# Set extra objects to manage on application start/shutdown
app["app_log"] = app_log
app["apscron_db"] = async_db_manager
app["apscheduler"] = scheduler

# Initialize database connection on application startup
app.on_startup.append(init_app)

# Close all acquired database connections on application tear down
app.on_cleanup.append(close_app)

# Set up application routes
setup_routes(app, routes)

# Set up application middlewares
setup_middlewares(app, middlewares)

if __name__ == "__main__":
    web.run_app(app, host=config.HOST, port=config.PORT)
