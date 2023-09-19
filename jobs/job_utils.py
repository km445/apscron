import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import COMMASPACE, formatdate


def send_email(subject, text, send_from, dest_to,
               server, port, user, password, attachments=[],
               is_html=False):
    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = send_from
    message["To"] = COMMASPACE.join(list(dest_to))
    message["Date"] = formatdate(localtime=True)
    if is_html:
        message.attach(MIMEText(text, "html"))
    else:
        message.attach(MIMEText(text))

    for attachment_path in attachments:
        with open(attachment_path, "rb") as attachment_file:
            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(attachment_file.read())
        encoders.encode_base64(attachment)
        attachment.add_header(
            "content-disposition", "attachment",
            filename=os.path.basename(attachment_path))
        message.attach(attachment)

    smtp_server = None
    try:
        smtp_server = smtplib.SMTP(host=server, port=port, timeout=3)
        smtp_server.connect(host=server, port=port)
        smtp_server.ehlo()
        smtp_server.starttls()
        smtp_server.login(user, password)
        smtp_server.sendmail(send_from, dest_to, message.as_string())
    finally:
        if smtp_server:
            smtp_server.quit()
