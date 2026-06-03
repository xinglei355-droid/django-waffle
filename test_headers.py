import os
import django
from django.conf import settings

settings.configure(
    DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
    INSTALLED_APPS=[
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'waffle',
    ],
    WAFFLE_OVERRIDE=True,
    WAFFLE_TEST_COOKIE='dwft_%s',
    WAFFLE_COOKIE='dwf_%s',
)
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser, User
from decimal import Decimal
from unittest import mock
from waffle.models import Flag

factory = RequestFactory()
request = factory.get('/foo', HTTP_DWFT_TEST_FLAG='1')
print("Headers:", request.headers)
print("dwft-test-flag in headers:", 'dwft-test-flag' in request.headers)
