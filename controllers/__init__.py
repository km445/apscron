import traceback
from datetime import datetime
from http import HTTPStatus
from importlib import import_module

from operator import attrgetter
from urllib.parse import unquote

from peewee import (AutoField, BigAutoField, IntegerField,
                    BigIntegerField, SmallIntegerField)
from aiohttp.web_response import StreamResponse
from aiohttp.web_exceptions import HTTPRedirection

import config
from constants import (LogType, filter_labels, ControllerResult, BSVariant,
                       BooleanType)
from models import ErrorLog, UserLog
from utils import get_request_data, flash
from responses import ControllerResponse
from exceptions import (HandledException, AuthorizationException,
                        ServiceException, AuthenticationException)


class BaseController(object):
    save_log = True
    auth_required = True
    # Permissions required to authorize request.
    # No authorization is required if both permissions lists are empty.
    # User is required to have all of required permissions
    # in order for request to work
    required_permissions = []
    # User needs any of related permissions
    # in order for request to work.
    # Generally can be used to get common data for select elements, etc
    # used in different views
    related_permissions = []

    def __init__(self, request, log_type):
        self.secret_fields = ["password"]
        self.request = request
        self.user = None
        self.class_name = self.__class__.__name__
        self.db = request.app["apscron_db"]
        self.log = request.app["app_log"]
        self.response_overrides = {}
        self.log_model = UserLog
        self.log_type = log_type
        self.auth_class = getattr(
            import_module(config.DEFAULT_AUTH_MODULE),
            config.DEFAULT_AUTH_CLASS)(self.request)

    async def _setup_log_data(self):
        self.request_data = await get_request_data(
            self.request, secret_fields=self.secret_fields)
        self.db_log_data = {
            "log_type": self.log_type,
            "request_data": self.request_data["log_data"],
            "request_ip": self.request_data["ip"],
            "request_url": self.request_data["url"],
            "request_method": self.request_data["method"],
            "request_headers": self.request_data["headers"],
            "response_data": ""}

    def _verify_request_data(self, required_keys):
        verified_data = {}
        for key in required_keys:
            if self.request_data["data"].get(key) in [None, ""]:
                raise ServiceException(
                    f"Invalid request, required key {key} is missing")
            verified_data[key] = self.request_data["data"].get(key)
        return verified_data

    def _verify_user_ip(self):
        if self.user and self.user.ip_list:
            if self.request.remote not in self.user.ip_list:
                raise AuthorizationException(
                    "Invalid IP %s for user %s" % (
                        self.request.remote, self.user.username))


class UniversalController(BaseController):
    text_filter_names = []
    select_filter_names = []
    daterange_filter_names = []
    text_like_filter_names = []

    async def call(self, *args, **kwargs):
        try:
            await self._setup_log_data()
            self.log.info("%s started with params: %s, %s, %s" %
                          (self.class_name,
                           self.db_log_data["request_data"], args, kwargs))
            if self.auth_required and self.auth_class:
                self.user = await self.auth_class._get_user()
                if not self.user.is_active:
                    raise AuthenticationException(
                        "User %s is disabled" % self.user.username)
                self._verify_user_ip()
            if self.user:
                if not self._has_authorization():
                    raise AuthorizationException()

            data = await self._call(*args, **kwargs)
            if isinstance(data, (StreamResponse, HTTPRedirection)):
                response = data
            else:
                response = ControllerResponse(
                    ControllerResult.Success, data=data)
            if not self.response_overrides.get("status"):
                self.response_overrides["status"] = HTTPStatus.OK
            self.log.info("%s finished" % self.class_name)
        except HandledException as e:
            response = self._handled_exception(e)
        except Exception as e:
            flash(self.request, str(e),
                  BSVariant.Danger.name, BSVariant.Danger.title)
            self.log.exception("%s finished with error" % self.class_name)
            await self.db.create(
                ErrorLog,
                request_data=self.request_data["log_data"],
                request_ip=self.request_data["ip"],
                request_url=self.request_data["url"],
                request_method=self.request_data["method"],
                error=e,
                traceback=traceback.format_exc())
            response = ControllerResponse(
                ControllerResult.Failure,
                messages=[{"message": str(e),
                           "variant": BSVariant.Danger.name,
                           "title": BSVariant.Danger.title}])
            self.response_overrides["status"] = (
                HTTPStatus.INTERNAL_SERVER_ERROR)
            self.db_log_data["error"] = e
        finally:
            if isinstance(response, ControllerResponse):
                response.overrides = self.response_overrides
            self.db_log_data["user"] = self.user
            self.db_log_data["finished_at"] = datetime.now()
            if self.save_log:
                await self.db.create(self.log_model, **self.db_log_data)
            return response

    async def _call(self, *args, **kwargs):
        raise NotImplementedError()

    def _select_query(self):
        return self.model.select()

    def _order_query(self, q):
        return q.order_by(self.model.id.desc())

    async def _filter_query(self, q):
        for arg in self.text_filter_names:
            parameter = self.request.query.get(arg)
            if parameter:
                attr = attrgetter(arg)(self.model)
                # Make parameter check if model attribute is of integer type
                if isinstance(
                    attr, (AutoField, BigAutoField, IntegerField,
                           BigIntegerField, SmallIntegerField)):
                    if not parameter.isdigit():
                        raise ServiceException(
                            "Invalid value %s for %s filter" % (
                                parameter, arg))
                q = q.where(attr == parameter)

        for arg in self.select_filter_names:
            if self.request.query.get(arg):
                parameter_list = unquote(
                    self.request.query.get(arg, "")).split(",")
                # Convert boolean text arg to python boolean type
                if any([BooleanType.FalseType.id in parameter_list,
                        BooleanType.TrueType.id in parameter_list]):
                    parameter_list = [
                        True if p == BooleanType.TrueType.id
                        else False if p == BooleanType.FalseType.id
                        else p for p in parameter_list]
                q = q.where(attrgetter(arg)(self.model) << parameter_list)

        for arg in self.daterange_filter_names:
            if self.request.query.get(arg):
                start, end = self.request.query.get(arg).split(" - ")
                start = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
                end = datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
                q = q.where(attrgetter(arg)(self.model).between(start, end))

        for arg in self.text_like_filter_names:
            if self.request.query.get(arg):
                q = q.where(
                    attrgetter(arg)(self.model).contains(
                        self.request.query.get(arg)))

        return self._order_query(q)

    def _get_page(self):
        curr_page = self.request.query.get(config.PAGE_PARAMETER)
        if curr_page and curr_page.isdigit():
            return int(curr_page)
        return 1

    async def _get_item_count(self, query):
        total_items = await self.db.count(query)
        return total_items

    def _get_list(self, query):
        return query.paginate(self._get_page(), config.ITEMS_PER_PAGE)

    async def _get_pagination(self, query):
        page = self._get_page()
        total_items = await self._get_item_count(query)
        return {"page": page,
                "total_items": total_items,
                "per_page": config.ITEMS_PER_PAGE}

    def _get_filters(self):
        filters = {}

        for key in self.text_filter_names:
            filters[key] = self._get_filter_for_text_input(key)

        for key in self.text_like_filter_names:
            filters[key] = self._get_filter_for_text_input(key)

        for key in self.select_filter_names:
            filters[key] = self._get_filter_for_select_input(key)

        for key in self.daterange_filter_names:
            filters[key] = self._get_filter_for_text_input(
                key, type_="daterange")

        return filters

    def _get_filter_for_text_input(self, key, type_="text"):
        label = filter_labels.get(key, key)
        return {"key": key,
                "label": label,
                "type": type_,
                "value": None}

    def _get_filter_for_select_input(self, key):
        options = []
        label = filter_labels.get(key, key)
        if key == "log_type":
            options = list(LogType.get_dicts())
        elif key in ["is_admin", "is_active"]:
            options = list(BooleanType.get_dicts())

        return {"key": key,
                "label": label,
                "type": "select",
                "options": options,
                "value": None}

    def _handled_exception(self, e):
        flash(self.request, str(e),
              BSVariant.Danger.name, BSVariant.Danger.title)
        self.log.warning(e)
        self.log.warning(traceback.format_exc())
        self.db_log_data["error"] = e
        response = ControllerResponse(
            ControllerResult.Failure,
            messages=[{"message": str(e),
                       "variant": BSVariant.Danger.name,
                       "title": BSVariant.Danger.title}])
        self.response_overrides["status"] = e.error_status
        return response

    def _has_authorization(self):
        if all([not self.related_permissions, not self.required_permissions]):
            return True
        if not self.user:
            raise AuthorizationException()
        if self.related_permissions:
            for p in self.related_permissions:
                if p in self.user.permissions:
                    return True
        if self.required_permissions:
            if set(
                self.required_permissions).issubset(
                    set(self.user.permissions)):
                return True
        return False
