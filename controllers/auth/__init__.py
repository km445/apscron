import base64
import hashlib

from constants import LogType, Permission
from controllers import UniversalController
from models import User
from exceptions import ServiceException


class LoginUserController(UniversalController):
    required_permissions = [Permission.UserLoginView.name]
    auth_required = False

    def __init__(self, request):
        super(LoginUserController, self).__init__(
            request, LogType.UserLoginView.id)
        self.secret_fields = ["password"]

    async def _call(self):
        verified_data = self._verify_request_data(("username", "password"))
        user = await self._verify_user(verified_data["username"])
        self.db_log_data["user"] = user
        self._verify_password(user, verified_data["password"])
        token_data = await self._login(user)
        self.db_log_data["response_data"] = token_data
        return token_data

    async def _verify_user(self, username):
        user = await User.get_by_kwargs(username=username)
        if not user:
            raise ServiceException(
                f"User with username {username} was not found")
        if not user.is_active:
            raise ServiceException(
                "User %s is disabled" % user.username)
        return user

    def _verify_password(self, user, password):
        salt = base64.b64decode(user.salt)
        db_password = base64.b64decode(user.password)
        hashed_password = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=1024, r=8, p=16)
        if db_password != hashed_password:
            raise ServiceException(f"User {user.username} password is wrong")

    async def _login(self, user):
        if self.auth_class:
            keep_loggged_in = self.request_data["data"].get("keep_logged_in")
            token_data = await self.auth_class._login(
                user, keep_loggged_in=keep_loggged_in)
            await self.db.update(user, only=[User.last_login_at])
            return token_data


class LogutUserController(UniversalController):
    required_permissions = [Permission.UserLogoutView.name]

    def __init__(self, request):
        super(LogutUserController, self).__init__(
            request, LogType.UserLogoutView.id)

    async def _call(self):
        if self.auth_class:
            await self.auth_class._logout()
