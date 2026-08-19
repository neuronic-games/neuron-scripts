# CSV audit log of sent emails: date/time, recipient address, attachment
# size, and whether the send succeeded (with the error if it didn't).
#
# Enable by setting settings.mail_log_folder to a folder path; leave
# it "" to disable. A single mail_log.csv file in that folder is appended
# to (with a header row written the first time), one row per send attempt
# (both successes and failures are logged).

import csv
import os
import logging
from datetime import datetime
import settings_loader  # must run before `import settings` below
import settings

_LOG_FILENAME = "mail_log.csv"


def log_sent(to_addr, attachment_size=None, success=True, error=None):
    """Call once per send attempt (success or failure). No-op unless
    settings.mail_log_folder is set.

    attachment_size: size of the attachment in bytes, or None if there
        wasn't one.
    success: whether the send succeeded.
    error: the error message, if success is False.
    """
    folder = getattr(settings, "mail_log_folder", "")
    if not folder:
        return

    try:
        os.makedirs(folder, exist_ok=True)
        log_file = os.path.join(folder, _LOG_FILENAME)
        write_header = not os.path.exists(log_file)
        with open(log_file, "a", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(
                    ["date_time", "email_address", "attachment_size_bytes", "success", "error"]
                )
            writer.writerow([
                datetime.now().isoformat(sep=" ", timespec="seconds"),
                to_addr,
                attachment_size if attachment_size is not None else "",
                success,
                error or "",
            ])
    except OSError as e:
        logging.warning("mail_log: could not write to mail_log_folder (%s): %s", folder, e)
