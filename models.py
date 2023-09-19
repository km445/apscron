import base64
import hashlib
import os
from datetime import datetime

from peewee import (Model, CharField, DateTimeField, ForeignKeyField,
                    TextField, IntegerField, BooleanField, DoubleField,
                    BlobField)
import peewee_async
import peewee_asyncext
from playhouse.postgres_ext import JSONField
from playhouse.pool import PooledPostgresqlExtDatabase

from config import DB_CONFIG
from constants import Permission

apscron_db = PooledPostgresqlExtDatabase(**DB_CONFIG)
apscron_db.commit_select = True
apscron_db.autorollback = True

# Set up async database and manager
db_name = DB_CONFIG.pop("database")
peewee_asyncext_db = peewee_asyncext.PooledPostgresqlExtDatabase(
    db_name, **DB_CONFIG)

async_db_manager = peewee_async.Manager(peewee_asyncext_db)
async_db_manager.database.set_allow_sync(False)


class _Model(Model):

    class Meta:
        database = apscron_db

    @classmethod
    async def get_by_id(cls, obj_id):
        try:
            obj = await async_db_manager.get(
                cls.select().where(cls.id == obj_id))
            return obj
        except cls.DoesNotExist:
            return None

    @classmethod
    async def get_by_kwargs(cls, **kwargs):
        try:
            obj = await async_db_manager.get(cls, **kwargs)
            return obj
        except cls.DoesNotExist:
            return None


class User(_Model):

    class Meta:
        table_name = "users"

    username = CharField(unique=True)
    password = CharField()
    salt = CharField()
    gauth = CharField(null=True)
    created_at = DateTimeField(default=datetime.now)
    last_login_at = DateTimeField(null=True)
    ip_list = JSONField(default=[])
    permissions = JSONField(default=[])
    is_admin = BooleanField(default=False)
    is_active = BooleanField(default=True)


class APSchedulerJob(_Model):

    class Meta:
        table_name = "apscheduler_jobs"

    id = CharField(primary_key=True)
    next_run_time = DoubleField(index=True, null=True)
    job_state = BlobField()


class UserLog(_Model):

    class Meta:
        table_name = "user_logs"

    user = ForeignKeyField(User, null=True, on_delete="CASCADE")
    log_type = IntegerField()
    request_data = TextField()
    request_ip = CharField(null=True)
    request_url = TextField()
    request_method = CharField()
    response_data = TextField()
    error = TextField(null=True)
    created_at = DateTimeField(default=datetime.now, index=True)
    finished_at = DateTimeField(null=True)


class JobLog(_Model):

    class Meta:
        table_name = "job_logs"

    user = ForeignKeyField(User, null=True, on_delete="CASCADE")
    job_id = CharField()
    job_data = JSONField(default={})
    job_result = JSONField(default={})
    error = TextField(null=True)
    started_at = DateTimeField(null=True)
    finished_at = DateTimeField(null=True)


class ErrorLog(_Model):

    class Meta:
        table_name = "error_logs"

    request_data = TextField()
    request_ip = CharField()
    request_url = CharField()
    request_method = CharField()
    error = TextField()
    traceback = TextField(null=True)
    created_at = DateTimeField(default=datetime.now)


def init_db():
    with async_db_manager.allow_sync():
        if apscron_db.is_closed():
            apscron_db.connect()
        tables_list = [User, APSchedulerJob, UserLog, JobLog, ErrorLog]
        if not any([t.table_exists() for t in tables_list]):
            apscron_db.drop_tables(tables_list, safe=True)
            print("Tables were dropped")
            apscron_db.create_tables(tables_list, safe=True)
            print("Tables were created")
            salt = os.urandom(128)
            password = "1"
            User.create(
                username="admin",
                password=base64.b64encode(
                    hashlib.scrypt(password.encode("utf-8"),
                                   salt=salt, n=1024, r=8, p=16)),
                salt=base64.b64encode(salt),
                permissions=[p.get("name") for p in Permission.get_dicts()],
                is_admin=True)
        apscron_db.close()


if __name__ == "__main__":
    init_db()
