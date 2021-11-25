from http import HTTPStatus

from controllers import UniversalController
from constants import Permission

import aiohttp_jinja2


class BaseFrontController(UniversalController):
    save_log = False

    def __init__(self, request):
        super(BaseFrontController, self).__init__(request, None)


class FrontLoginController(BaseFrontController):
    auth_required = False

    async def _call(self):
        return aiohttp_jinja2.render_template(
            "auth/login.html", self.request, {})


class FrontGetUsersController(BaseFrontController):
    related_permissions = [Permission.UserListView.name]

    async def _call(self):
        return aiohttp_jinja2.render_template(
            "users/list.html", self.request, {})


class FrontPostUsersController(BaseFrontController):
    related_permissions = [Permission.UserAddView.name]

    async def _call(self):
        return aiohttp_jinja2.render_template(
            "users/add.html", self.request, {})


class FrontGetUserController(BaseFrontController):
    related_permissions = [
        Permission.UserGetView.name,
        Permission.UserEditView.name]

    async def _call(self):
        return aiohttp_jinja2.render_template(
            "users/edit.html", self.request, {**self.request.match_info})


class FrontGetJobsController(BaseFrontController):
    related_permissions = [Permission.JobListView.name]

    async def _call(self):
        return aiohttp_jinja2.render_template(
            "jobs/list.html", self.request, {})


class FrontPostJobsController(BaseFrontController):
    related_permissions = [Permission.JobAddView.name]

    async def _call(self):
        return aiohttp_jinja2.render_template(
            "jobs/add.html", self.request, {})


class FrontGetJobController(BaseFrontController):
    related_permissions = [
        Permission.JobGetView.name,
        Permission.JobEditView.name]

    async def _call(self):
        return aiohttp_jinja2.render_template(
            "jobs/edit.html", self.request, {**self.request.match_info})


class FrontLogController(BaseFrontController):
    related_permissions = [
        Permission.UserLogView.name,
        Permission.JobLogView.name,
        Permission.ErrorLogView.name]

    async def _call(self, log_type):
        return aiohttp_jinja2.render_template(
            "logs/list.html", self.request, {"log_type": log_type})


class FrontErrorController(BaseFrontController):
    auth_required = False

    async def _call(self):
        return aiohttp_jinja2.render_template(
            "errors/error.html", self.request, {},
            status=HTTPStatus.INTERNAL_SERVER_ERROR)
