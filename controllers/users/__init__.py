import os
import json
import base64
import hashlib
import ipaddress

from constants import LogType, Permission, BSVariant
from controllers import UniversalController
from models import User
from utils import flash, convert_types
from exceptions import ServiceException


class BaseUserController(UniversalController):

    def _validate_ip_list(self, ip_list):
        for ip in ip_list:
            try:
                ipaddress.ip_address(ip)
            except (ValueError, ipaddress.AddressValueError):
                raise ServiceException("Invalid IP format: %s" % ip)
        return ip_list

    async def _verify_permissions(self):
        permissions = self.request_data["data"].get("permissions", [])
        allowed_permissions = [permission.get("name")
                               for permission in list(Permission.get_dicts())]
        for permission in permissions:
            if permission not in allowed_permissions:
                raise ServiceException(
                    "Unable to add user. Invalid permission %s" % permission)
        self.db_log_data["request_data"]["permissions"] = permissions
        return permissions

    async def _verify_user(self, id_):
        user = await User.get_by_kwargs(id=id_)
        if not user:
            raise ServiceException(f"User with id {id_} was not found")
        return user


class UserListController(BaseUserController):
    text_filter_names = ("id",)
    select_filter_names = ("is_admin", "is_active")
    daterange_filter_names = ("created_at", "last_login_at")
    text_like_filter_names = ("username",)
    model = User
    required_permissions = [Permission.UserListView.name]

    def __init__(self, request):
        super(UserListController, self).__init__(
            request, LogType.UserListView.id)
        self.save_log = False

    async def _call(self):
        query = self._select_query()
        result = await self._filter_query(query)
        users = json.dumps(
            list(await self.db.execute(self._get_list(result).dicts())),
            default=convert_types)
        pagination = await self._get_pagination(result)
        return {"items": json.loads(users),
                "filters": self._get_filters(),
                "pagination": pagination}

    def _select_query(self):
        return self.model.select(
            self.model.id, self.model.username, self.model.created_at,
            self.model.last_login_at, self.model.ip_list,
            self.model.permissions, self.model.is_admin, self.model.is_active)

    def _order_query(self, q):
        return q.order_by(self.model.id.asc())


class UserAddController(BaseUserController):
    required_permissions = [Permission.UserAddView.name]

    def __init__(self, request):
        super(UserAddController, self).__init__(
            request, LogType.UserAddView.id)
        self.secret_fields = ["password", "gauth"]

    async def _call(self):
        verified_data = self._verify_request_data(
            ("username", "password", "ip_list"))
        username = await self._verify_username(verified_data["username"])
        password, salt = self._verify_password(verified_data["password"])
        ip_list = self._validate_ip_list(verified_data["ip_list"])
        gauth = self.request_data["data"].get("gauth")
        permissions = await self._verify_permissions()
        is_admin = bool(self.request_data["data"].get("is_admin"))
        is_active = bool(self.request_data["data"].get("is_active"))

        user = await self.db.create(
            User, username=username, password=password,
            salt=salt, gauth=gauth, ip_list=ip_list,
            permissions=permissions, is_admin=is_admin,
            is_active=is_active)
        response_data = {
            "id": user.id, "username": user.username,
            "permissions": user.permissions, "is_admin": user.is_admin,
            "is_active": user.is_active, "ip_list": user.ip_list}
        self.db_log_data["response_data"] = response_data
        flash(self.request, "New user %s has been created" % user.username,
              BSVariant.Success.name, BSVariant.Success.title)
        return response_data

    def _verify_password(self, password):
        if not password:
            raise ServiceException("Specify password")

        salt = os.urandom(128)
        password = base64.b64encode(
            hashlib.scrypt(str(password).encode("utf-8"),
                           salt=salt, n=1024, r=8, p=16))
        salt = base64.b64encode(salt)

        return password, salt

    async def _verify_username(self, username):
        if not username:
            raise ServiceException("Username is not valid")

        user = await User.get_by_kwargs(username=username)
        if user:
            raise ServiceException(
                f"User with username {username} already exists")
        return username


class UserEditController(BaseUserController):

    def __init__(self, request):
        if request.method == "GET":
            log_type = LogType.UserGetView.id
            required_permissions = [Permission.UserGetView.name]
        else:
            log_type = LogType.UserEditView.id
            required_permissions = [Permission.UserEditView.name]
        super(UserEditController, self).__init__(request, log_type)
        self.required_permissions = required_permissions
        self.secret_fields = ["password", "gauth"]

    async def _call(self, user_id):
        user = await self._verify_user(user_id)
        if self.request.method == "GET":
            user = dict(user.__data__)
            user_data = {}
            for k, v in user.items():
                if k in ["id", "username", "ip_list",
                         "permissions", "is_admin", "is_active"]:
                    user_data[k] = v
                else:
                    user_data[k] = ''
            self.save_log = False
            return user_data

        verified_data = self._verify_request_data(("username", "ip_list"))
        user.username = await self._verify_username(
            user.username, verified_data["username"])
        password, salt = self._verify_password(
            self.request_data["data"].get("password"))
        user.ip_list = self._validate_ip_list(verified_data["ip_list"])
        gauth = self.request_data["data"].get("gauth")
        user.permissions = await self._verify_permissions()
        user.is_admin = bool(self.request_data["data"].get("is_admin"))
        user.is_active = bool(self.request_data["data"].get("is_active"))

        if password and salt:
            user.password = password
            user.salt = salt
        if gauth:
            user.gauth = gauth

        await self.db.update(user)
        response_data = {
            "id": user.id, "username": user.username,
            "permissions": user.permissions, "is_admin": user.is_admin,
            "is_active": user.is_active, "ip_list": user.ip_list}
        self.db_log_data["response_data"] = response_data
        flash(self.request, "User %s has been updated" % user.username,
              BSVariant.Success.name, BSVariant.Success.title)
        return response_data

    def _verify_password(self, password):
        if password:
            salt = os.urandom(128)
            password = base64.b64encode(
                hashlib.scrypt(str(password).encode("utf-8"),
                               salt=salt, n=1024, r=8, p=16))
            salt = base64.b64encode(salt)

            return password, salt

        return None, None

    async def _verify_username(self, old_username, new_username):
        if not new_username:
            raise ServiceException("Username is not valid")

        if new_username != old_username:
            user = await User.get_by_kwargs(username=new_username)
            if user:
                raise ServiceException(
                    "User with username %s already exists" % new_username)

        return new_username


class UserDeleteController(BaseUserController):
    required_permissions = [Permission.UserDeleteView.name]

    def __init__(self, request):
        super(UserDeleteController, self).__init__(
            request, LogType.UserDeleteView.id)

    async def _call(self, user_id):
        user = await self._verify_user(user_id)
        await self.db.delete(user)
        message = "User %s has been deleted" % user.username
        response_data = {"message": message}
        self.db_log_data["response_data"] = response_data
        flash(self.request, message,
              BSVariant.Danger.name, BSVariant.Warning.title)
        return response_data


class CommonUserDataController(BaseUserController):
    related_permissions = [
        Permission.JobAddView.name,
        Permission.JobGetView.name]

    def __init__(self, request):
        super(CommonUserDataController, self).__init__(
            request, LogType.CommonUserDataView.id)

    async def _call(self):
        return {"permissions": list(Permission.get_dicts())}
