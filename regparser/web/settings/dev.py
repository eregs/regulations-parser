from regparser.web.settings.base import *  # noqa

# You need to have an email server running locally for this to work.
# ``python -m smtpd -n -c DebuggingServer localhost:2525`` should be fine.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "127.0.0.1"
EMAIL_PORT = 2525
