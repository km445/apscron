import socket
import asyncio
from datetime import datetime

from jinja2 import Template
from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError

import config
from jobs import BaseJobController
from jobs.job_utils import send_email


class APSJob(BaseJobController):
    """
    <div>
    Monitor Sockets - check if URLs like https://www.google.com/ are responding
    with Status Code: 200 OK.
    Note: Actual amount of checks/requests is hosts multiplied by url_templates
    <br><br>
    <b>Example config:</b><br>
    {<br>
     "hosts": ["www.google.com"],<br>
     "url_templates": ["https://%s"],<br>
     "emails": ["user@your_mail_server.com"],<br>
     "timeout": 9<br>
    }
    <br><br>
    <b>Required parameters:</b><br>
    <b>hosts</b> - Required. List of hosts.
    Example: ["www.google.com"]<br>
    <b>url_templates</b> - Required. List of url templates.
    Leave %s instead of host.
    Example: ["https://%s"]<br>
    <b>emails</b> - Required. List of emails to which report is sent.
    Example: ["user@your_mail_server.com"]
    <br><br>
    <b>Optional parameters:</b><br>
    <b>timeout</b> - Optional. Request timeout.
    Amount of seconds allowed to fetch a single URL.
    Default is 30. Do not set too low timeout, as it will result in connect
    timeout error.<br>
    </div>
    """

    async def _call(self, **kwargs):
        self._verify_job_kwargs(kwargs, ["hosts", "url_templates", "emails"])
        to_emails = kwargs.get("emails")
        timeout = kwargs.get("timeout")
        if timeout:
            timeout = float(timeout)
        else:
            timeout = float(30)

        tasks = []
        request_urls = []
        async with ClientSession(
                timeout=ClientTimeout(total=timeout)) as session:
            for host in kwargs.get("hosts"):
                for ut in kwargs.get("url_templates"):
                    url = ut % host
                    tasks.append(self.send_request(session, "GET", host, url))
                    request_urls.append(url)
            result = await asyncio.gather(*tasks, return_exceptions=True)
            await session.close()
        failed_resp = []
        subject = "APSCron Monitor Socket %s" % datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S")
        j_template = Template("""
        <html>
        <head><title>{{ subject }}</title></head>
        <body>
        {% for item in failed_resp %}
        {% if item.get("error") %}
        <div>
            <p>
                <b>Request URL:</b>
                <a href="{{ item.get("url") }}">{{ item.get("url") }}</a>
            </p>
            <p>
                <b>Error:</b> {{ item.get("error") }}
            </p>
        </div>
        {% else %}
        <div>
            <p>
                <b>Request URL:</b>
                <a href="{{ item.get("url") }}">{{ item.get("url") }}</a>
            </p>
            <p><b>Request Method:</b> {{ item.get("method") }}</p>
            <p>
                <b>Status Code:</b>
                {{item.get("status")}} {{item.get("status_text")}}
            </p>
            <p><b>Remote Address:</b> {{item.get("ip")}}</p>
        </div>
        {% endif %}
        <hr>
        {% endfor %}
        </body>
        </html>
        """)
        for index, item in enumerate(result):
            if isinstance(item, ClientError):
                failed_resp.append(
                    {"url": request_urls[index],
                     "error": " ".join([item.__class__.__name__, str(item)])})
            elif isinstance(item, dict) and item.get("status") != 200:
                failed_resp.append(item)
        self.job_result["result"] = failed_resp
        if failed_resp:
            html = j_template.render(subject=subject, failed_resp=failed_resp)
            send_email(subject, html, config.SMTP_USER, to_emails,
                       config.SMTP_HOST, config.SMTP_PORT, config.SMTP_USER,
                       config.SMTP_PASSWORD, is_html=True)
        self.db_log_data["finished_at"] = datetime.now()

    async def send_request(self, session, method, host, url):
        resp = await session.request(method, url)
        try:
            ip = socket.gethostbyname(host)
        except Exception:
            ip = "Failed to resolve IP"
        return {"status": resp.status, "status_text": resp.reason,
                "url": url, "ip": ip, "method": method}
