from datetime import datetime, timedelta

import jwt

from aiohttp_session import new_session, get_session

import config
from models import User
from utils import flash, get_token, set_session_user
from constants import BSVariant
from exceptions import AuthenticationException


class TokenAuth(object):
    """Handles JWT auth.

    Returns user instance if request has valid auth token.
    Otherwise raises AuthenticationException with proper message/http code.
    """

    def __init__(self, request):
        super(TokenAuth, self).__init__()
        self.request = request
        self.auth_header = config.DEFAULT_AUTH_HEADER

    async def _login(
            self,
            user,
            expiration_minutes=config.DEFAULT_AUTH_EXPIRATION,
            keep_loggged_in=False):
        """Perform user login where user is a User model instance.

        Return token data.
        """
        session = await new_session(self.request)
        user.last_login_at = datetime.now()
        expiration = datetime.utcnow()
        if keep_loggged_in:
            expiration += timedelta(days=365)
        else:
            expiration += timedelta(minutes=expiration_minutes)
        token = jwt.encode(
            {"user_id": user.id, "exp": expiration},
            config.JWT_SIGN_KEY,
            algorithm=config.JWT_SIGN_ALGORITHM)
        session["token"] = token
        user_data = set_session_user(session, user)
        flash(self.request, "Login successful",
              BSVariant.Success.name, BSVariant.Success.title)
        return {"token": token,
                "user": user_data,
                "expiration_utc": str(expiration)}

    async def _logout(self):
        """Logout user by blacklisting token."""
        token = get_token(self.request)
        if token and token not in config.BLACKLISTED_JWT:
            config.BLACKLISTED_JWT.append(token)
        session = await get_session(self.request)
        session.clear()
        flash(self.request, "Logout successful",
              BSVariant.Success.name, BSVariant.Success.title)

    async def _get_user(self):
        """Get user from request where user is a User model instance."""
        session = await get_session(self.request)
        token = get_token(self.request)
        if not token:
            token = session.get("token")
        if not token:
            raise AuthenticationException("Missing auth token")

        if token in config.BLACKLISTED_JWT:
            raise AuthenticationException("Blacklisted token")
        try:
            token_data = jwt.decode(
                token,
                config.JWT_SIGN_KEY,
                algorithms=config.JWT_SIGN_ALGORITHM)
        except jwt.exceptions.InvalidTokenError:
            raise AuthenticationException("Invalid token")
        user = await User.get_by_id(token_data.get("user_id"))
        if not user:
            raise AuthenticationException("Please log in")
        else:
            if not user.is_active:
                raise AuthenticationException("User is not active")
            set_session_user(session, user)
        return user
