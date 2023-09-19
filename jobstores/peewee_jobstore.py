from __future__ import absolute_import
try:
    import cPickle as pickle
except ImportError:  # pragma: nocover
    import pickle

from apscheduler.jobstores.base import BaseJobStore
from apscheduler.jobstores.base import JobLookupError
from apscheduler.jobstores.base import ConflictingIdError
from apscheduler.util import datetime_to_utc_timestamp
from apscheduler.util import utc_timestamp_to_datetime
from apscheduler.job import Job

from peewee import IntegrityError

from models import APSchedulerJob


class PeeweeJobStore(BaseJobStore):
    """
    Stores jobs in a database table using Peewee ORM.
    The table will be created if it doesn't exist in the database.

    :param int pickle_protocol: pickle protocol level to use
        (for serialization), defaults to the highest available
    """

    def __init__(self, pickle_protocol=pickle.HIGHEST_PROTOCOL,
                 jobs_t=APSchedulerJob):
        super(PeeweeJobStore, self).__init__()
        self.pickle_protocol = pickle_protocol

        self.jobs_t = jobs_t

    def start(self, scheduler, alias):
        super(PeeweeJobStore, self).start(scheduler, alias)
        if self.jobs_t._meta.database.is_closed():
            self.jobs_t._meta.database.connect()
        self.jobs_t.create_table(safe=True)

    def lookup_job(self, job_id):
        res = (self.jobs_t
               .select(self.jobs_t.job_state)
               .where(self.jobs_t.id == job_id)
               .first())
        return self._reconstitute_job(res.job_state) if res else None

    def get_due_jobs(self, now):
        timestamp = datetime_to_utc_timestamp(now)
        return self._get_jobs(self.jobs_t.next_run_time <= timestamp)

    def get_next_run_time(self):
        res = (self.jobs_t
               .select(self.jobs_t.next_run_time)
               .where(self.jobs_t.next_run_time.is_null(False))
               .order_by(self.jobs_t.next_run_time)
               .first())
        return utc_timestamp_to_datetime(res.next_run_time) if res else None

    def get_all_jobs(self):
        jobs = self._get_jobs()
        self._fix_paused_jobs_sorting(jobs)
        return jobs

    def add_job(self, job):
        try:
            (self.jobs_t
                .insert(
                    id=job.id,
                    next_run_time=datetime_to_utc_timestamp(job.next_run_time),
                    job_state=pickle.dumps(
                        job.__getstate__(), self.pickle_protocol))
                .execute())
        except IntegrityError:
            raise ConflictingIdError(job.id)

    def update_job(self, job):
        res = (self.jobs_t
               .update(next_run_time=datetime_to_utc_timestamp(
                       job.next_run_time),
                       job_state=pickle.dumps(
                       job.__getstate__(), self.pickle_protocol))
               .where(self.jobs_t.id == job.id)
               .execute())
        if res == 0:
            raise JobLookupError(job.id)

    def remove_job(self, job_id):
        res = (self.jobs_t
               .delete()
               .where(self.jobs_t.id == job_id)
               .execute())
        if res == 0:
            raise JobLookupError(job_id)

    def remove_all_jobs(self):
        self.jobs_t.delete().execute()

    def shutdown(self):
        if not self.jobs_t._meta.database.is_closed():
            self.jobs_t._meta.database.close()

    def _reconstitute_job(self, job_state):
        job_state = pickle.loads(job_state)
        job_state['jobstore'] = self
        job = Job.__new__(Job)
        job.__setstate__(job_state)
        job._scheduler = self._scheduler
        job._jobstore_alias = self._alias
        return job

    def _get_jobs(self, *conditions):
        jobs = []
        selectable = (self.jobs_t
                      .select(self.jobs_t.id, self.jobs_t.job_state)
                      .order_by(self.jobs_t.next_run_time))
        selectable = (selectable.where(*conditions)
                      if conditions else selectable)

        failed_job_ids = set()
        for row in list(selectable):
            try:
                jobs.append(self._reconstitute_job(row.job_state))
            except BaseException:
                self._logger.exception(
                    "Unable to restore job '%s' -- removing it", row.id)
                failed_job_ids.add(row.id)

        # Remove all the jobs we failed to restore
        if failed_job_ids:
            (self.jobs_t
                .delete()
                .where(self.jobs_t.id.in_(failed_job_ids))
                .execute())

        return jobs

    def __repr__(self):
        return "<%s>" % (self.__class__.__name__)
