import os
import logging
from datetime import date

# APScron application host and port
HOST = "0.0.0.0"
PORT = 6999
COOKIE_NAME = "APScron_session"

# Cookie max age in seconds
MAX_AGE = 60 * 60

# Both signing key and blacklist are reset when application restarts
JWT_SIGN_KEY = str(os.urandom(32))
JWT_SIGN_ALGORITHM = "HS256"
BLACKLISTED_JWT = []

# APScron database settings
DB_CONFIG = {"user": "apscron",
             "password": "apscron",
             "host": "postgresql_apscron_db",
             "port": 5432,
             "database": "apscron",
             "max_connections": 20,
             "connect_timeout": 5,
             "register_hstore": False,
             "server_side_cursors": False}

# APScron logging settings
DIRS = {
    "LOG_TO": os.path.join(os.path.expanduser("~"), "logs/apscron"),
    "BASE_DIR": os.path.dirname(os.path.abspath(__file__))
}
DIRS["TEMPLATE_DIR"] = os.path.join(DIRS["BASE_DIR"], 'templates')

LOGGER = {
    "level": logging.DEBUG,
    "file": "log_{date:%Y-%m-%d}.log".format(date=date.today()),
    "formatter": logging.Formatter("%(asctime)s [%(thread)d:%(threadName)s] "
                                   "[%(levelname)s] - %(name)s: %(message)s"),
    "peewee_file": "peewee_log_{date:%Y-%m-%d}.log".format(
        date=date.today()),
    "apscron_file": "apscron_log_{date:%Y-%m-%d}.log".format(
        date=date.today())
}

# Jobs default timezone
DEFAULT_TIMEZONE = "EET"

# Pagination parameters
PAGE_PARAMETER = "page"
ITEMS_PER_PAGE = 25

# Host for static/media files; leave empty string for localhost.
# Production/stage values have to look like "https://static.host.com" or
# "//static.host.com" to let browser choose protocol automatically
STATIC_PATH_URL = ""

# SMTP server settings
SMTP_HOST = "smtp.your_mail_server.com"
SMTP_PORT = 587
SMTP_USER = "user@your_mail_server.com"
SMTP_PASSWORD = "password"

# Default authentication class, performs authentication via
# Authorization/cookie request header
DEFAULT_AUTH_MODULE = "auth"
DEFAULT_AUTH_CLASS = "TokenAuth"
DEFAULT_AUTH_HEADER = "Authorization"
# Token expiration in minutes
DEFAULT_AUTH_EXPIRATION = 60
