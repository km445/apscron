import os
import base64
import hashlib
import uuid
from http import HTTPStatus

import jinja2
import aiohttp_jinja2
import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor

from cryptography import fernet
from aiohttp import web
from aiohttp_session import setup as aiohttp_session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from pytz import utc

import config
from views import routes
from utils import (setup_routes, setup_middlewares, get_log, init_app,
                   close_app, setup_template_functions)
from middlewares import middlewares
from jobstores.peewee_jobstore import PeeweeJobStore
from models import async_db_manager, User, UserLog
from constants import ControllerResult, Permission, LogType
from exceptions import MethodNotAllowedException


def create_example_app():
    # Get WSGI application and set up logging
    app = web.Application()
    app_log = get_log(
        os.path.join(config.DIRS["LOG_TO"], config.LOGGER["file"]),
        config.LOGGER["level"], config.LOGGER["formatter"], "apscron")

    # Setup encrypted cookie session
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)
    aiohttp_session_setup(app, EncryptedCookieStorage(
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
    return app


username = str(uuid.uuid4())
user = User.get_or_none(username=username)
if not user:
    salt = os.urandom(128)
    password = "1"
    user = User.create(
        username=username,
        password=base64.b64encode(
            hashlib.scrypt(password.encode("utf-8"),
                           salt=salt, n=1024, r=8, p=16)).decode('utf-8'),
        salt=base64.b64encode(salt),
        permissions=[p.get("name") for p in Permission.get_dicts()],
        is_admin=True,
        is_active=True)


async def get_token_auth_header(client):
    login_data = {"username": username, "password": password}
    resp = await client.post("/auth/login", json=login_data)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    token = data.get("data", {}).get("token")
    assert token is not None
    user = data.get("data", {}).get("user")
    assert user is not None
    assert isinstance(user, dict)
    assert user.get("username") == login_data["username"]
    return {"Authorization": "Bearer %s" % token}


@pytest.fixture
def client(loop, aiohttp_client):
    app = create_example_app()
    return loop.run_until_complete(aiohttp_client(app))


@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    def remove_test_user_footprint():
        UserLog.delete().where(UserLog.user == user).execute()
        user.delete_instance(recursive=True)
    request.addfinalizer(remove_test_user_footprint)


async def test_get_common_user_data(client):
    auth_header = await get_token_auth_header(client)
    resp = await client.get("/users_common_data", headers=auth_header)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    assert "permissions" in data["data"]
    assert data["data"]["permissions"] == list(Permission.get_dicts())
    resp = await client.post("/users_common_data", headers=auth_header)
    assert resp.status == HTTPStatus.METHOD_NOT_ALLOWED
    data = await resp.json()
    assert data["ok"] == ControllerResult.Failure
    messages = data.get("messages")
    assert isinstance(messages, list)
    assert len(messages)
    assert messages[0].get(
        "message") == MethodNotAllowedException.error_message


async def test_post_users_add_and_users_delete(client):
    auth_header = await get_token_auth_header(client)
    user_data = {"username": str(uuid.uuid4()), "password": 1,
                 "ip_list": [], "is_admin": False,
                 "is_active": False, "permissions": []}
    resp = await client.post("/users", json=user_data, headers=auth_header)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    assert len(messages)
    assert messages[0].get(
        "message") == "New user %s has been created" % user_data["username"]
    assert data["data"]["username"] == user_data["username"]
    assert data["data"]["ip_list"] == user_data["ip_list"]
    assert data["data"]["is_admin"] == user_data["is_admin"]
    assert data["data"]["is_active"] == user_data["is_active"]
    assert data["data"]["permissions"] == user_data["permissions"]
    log = UserLog.get_or_none(
        user_id=user.id, log_type=LogType.UserAddView.id)
    assert log is not None
    assert log.request_method == "POST"
    user_id = data["data"]["id"]
    resp = await client.delete("/users/%s" % user_id, headers=auth_header)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    assert len(messages)
    assert messages[0].get(
        "message") == "User %s has been deleted" % user_data["username"]
    log = UserLog.get_or_none(
        user_id=user.id, log_type=LogType.UserDeleteView.id)
    assert log is not None
    assert log.request_method == "DELETE"


async def test_get_users_list(client):
    auth_header = await get_token_auth_header(client)
    request_params = {"id": user.id}
    resp = await client.get(
        "/users", headers=auth_header, params=request_params)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    user_list = data["data"]["items"]
    assert len(user_list) == 1
    user_data = user_list[0]
    assert user_data["id"] == user.id
    assert user_data["username"] == user.username
    assert user_data["ip_list"] == user.ip_list
    assert user_data["permissions"] == user.permissions
    assert user_data["is_admin"] == user.is_admin
    assert user_data["is_active"] == user.is_active
    log = UserLog.get_or_none(
        user_id=user.id, log_type=LogType.UserListView.id)
    assert log is None
    resp = await client.put(
        "/users", headers=auth_header, params=request_params)
    assert resp.status == HTTPStatus.METHOD_NOT_ALLOWED
    data = await resp.json()
    assert data["ok"] == ControllerResult.Failure
    messages = data.get("messages")
    assert isinstance(messages, list)
    assert len(messages)
    assert messages[0].get(
        "message") == MethodNotAllowedException.error_message
    assert data["data"] is None


async def test_get_and_put_users_edit(client):
    auth_header = await get_token_auth_header(client)
    resp = await client.get("/users/%s" % user.id, headers=auth_header)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    user_data = data["data"]
    assert user_data["id"] == user.id
    assert user_data["username"] == user.username
    assert user_data["ip_list"] == user.ip_list
    assert user_data["permissions"] == user.permissions
    assert user_data["is_admin"] == user.is_admin
    assert user_data["is_active"] == user.is_active
    log = UserLog.get_or_none(
        user_id=user.id, log_type=LogType.UserGetView.id)
    assert log is None
    request_data = {"username": user.username, "permissions": user.permissions,
                    "ip_list": [], "is_admin": False, "is_active": True}
    resp = await client.put(
        "/users/%s" % user.id, json=request_data, headers=auth_header)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    assert len(messages)
    assert messages[0].get(
        "message") == "User %s has been updated" % user_data["username"]
    user_data = data["data"]
    assert user_data["id"] == user.id
    assert user_data["username"] == user.username
    assert user_data["ip_list"] == user.ip_list
    assert user_data["permissions"] == user.permissions
    assert user_data["is_admin"] is False
    assert user_data["is_active"] is True
    log = (UserLog.
           select().
           where(UserLog.user_id == user.id,
                 UserLog.log_type == LogType.UserEditView.id).
           order_by(UserLog.id.desc()).
           first())
    assert log is not None
    assert log.request_method == "PUT"


async def test_post_jobs_and_jobs_delete(client):
    auth_header = await get_token_auth_header(client)
    job_data = {"name": str(uuid.uuid4()), "module": "test_job",
                "trigger": "cron", "kwargs": {"test": True},
                "year": "*", "month": "*", "day": "*", "week": "*",
                "day_of_week": "*", "hour": "*", "minute": "*", "second": "0"}

    resp = await client.post("/jobs", json=job_data, headers=auth_header)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    assert len(messages)
    assert messages[0].get(
        "message") == "New job %s has been added" % data["data"]["job_id"]
    assert data["data"]["job_name"] == job_data["name"]
    assert data["data"]["job_kwargs"] == job_data["kwargs"]
    log = UserLog.get_or_none(
        user_id=user.id, log_type=LogType.JobAddView.id)
    assert log is not None
    assert log.request_method == "POST"
    job_id = data["data"]["job_id"]
    resp = await client.delete("/jobs/%s" % job_id, headers=auth_header)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    assert len(messages)
    assert messages[0].get(
        "message") == "Job %s has been deleted" % job_id
    log = UserLog.get_or_none(
        user_id=user.id, log_type=LogType.JobDeleteView.id)
    assert log is not None
    assert log.request_method == "DELETE"


async def test_get_and_put_job(client):
    auth_header = await get_token_auth_header(client)
    job_data = {"name": str(uuid.uuid4()), "module": "test_job",
                "trigger": "cron", "kwargs": {"test": True},
                "year": "*", "month": "*", "day": "*", "week": "*",
                "day_of_week": "*", "hour": "*", "minute": "*", "second": "0"}

    resp = await client.post("/jobs", json=job_data, headers=auth_header)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    assert len(messages)
    assert messages[0].get(
        "message") == "New job %s has been added" % data["data"]["job_id"]
    assert data["data"]["job_name"] == job_data["name"]
    assert data["data"]["job_kwargs"] == job_data["kwargs"]
    job_id = data["data"]["job_id"]
    resp = await client.get("/jobs/%s" % job_id, headers=auth_header)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    resp_data = data["data"]
    assert resp_data["name"] == job_data["name"]
    assert resp_data["kwargs"] == job_data["kwargs"]
    assert resp_data["module"] == job_data["module"]
    request_data = dict(job_data)
    request_data["name"] = str(uuid.uuid4())
    resp = await client.put(
        "/jobs/%s" % job_id, json=request_data, headers=auth_header)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    assert len(messages)
    job_data = data["data"]
    assert messages[0].get(
        "message") == "Job %s has been updated" % data["data"]["job_id"]
    assert job_data["job_name"] == request_data["name"]
    log = (UserLog.
           select().
           where(UserLog.user_id == user.id,
                 UserLog.log_type == LogType.JobEditView.id).
           order_by(UserLog.id.desc()).
           first())
    assert log is not None
    assert log.request_method == "PUT"


async def test_pause_and_resume_job(client):
    auth_header = await get_token_auth_header(client)
    job_data = {"name": str(uuid.uuid4()), "module": "test_job",
                "trigger": "cron", "kwargs": {"test": True},
                "year": "*", "month": "*", "day": "*", "week": "*",
                "day_of_week": "*", "hour": "*", "minute": "*", "second": "0"}
    resp = await client.post("/jobs", json=job_data, headers=auth_header)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    assert len(messages)
    assert messages[0].get(
        "message") == "New job %s has been added" % data["data"]["job_id"]
    assert data["data"]["job_name"] == job_data["name"]
    assert data["data"]["job_kwargs"] == job_data["kwargs"]
    job_id = data["data"]["job_id"]
    resp = await client.post("/jobs/pause/%s" % job_id, headers=auth_header)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    assert len(messages)
    assert messages[0].get(
        "message") == "Job %s has been paused" % job_id
    log = UserLog.get_or_none(
        user_id=user.id, log_type=LogType.JobPauseView.id)
    assert log is not None
    assert log.request_method == "POST"
    resp = await client.post("/jobs/pause/%s" % job_id, headers=auth_header)
    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["ok"] == ControllerResult.Success
    messages = data.get("messages")
    assert isinstance(messages, list)
    assert len(messages)
    assert messages[0].get(
        "message") == "Job %s has been resumed" % job_id
    log = UserLog.get_or_none(
        user_id=user.id, log_type=LogType.JobPauseView.id)
    assert log is not None
    assert log.request_method == "POST"
