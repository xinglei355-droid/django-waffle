#!/usr/bin/env python
import os
import django
from django.conf import settings
from django.http import HttpResponse, HttpRequest
from waffle.middleware import WaffleMiddleware
import waffle.defaults

# Configure Django settings
settings.configure(
    DEBUG=True,
    ROOT_URLCONF='',
    INSTALLED_APPS=[
        'django.contrib.contenttypes',
        'django.contrib.auth',
    ],
    WAFFLE_COOKIE=waffle.defaults.COOKIE,
    WAFFLE_MAX_AGE=waffle.defaults.MAX_AGE,
    WAFFLE_SECURE=waffle.defaults.SECURE,
)

django.setup()

print("Testing current WaffleMiddleware behavior...")
print(f"MAX_AGE is: {settings.WAFFLE_MAX_AGE}")
print("=" * 80)

# Test all four combinations
test_cases = [
    ('case1', True, True),    # active=True, rollout=True
    ('case2', False, True),   # active=False, rollout=True
    ('case3', True, False),   # active=True, rollout=False
    ('case4', False, False),  # active=False, rollout=False
]

request = HttpRequest()
request.waffles = {name: (active, rollout) for name, active, rollout in test_cases}
response = HttpResponse()
response = WaffleMiddleware().process_response(request, response)

for name, active, rollout in test_cases:
    cookie_name = f'dwf_{name}'
    cookie = response.cookies[cookie_name]
    
    max_age_set = bool(cookie.get('max-age'))
    print(f"{name}: active={active}, rollout={rollout}")
    print(f"  cookie.value: {cookie.value}")
    print(f"  has max-age: {max_age_set}")
    if 'max-age' in cookie:
        print(f"  max-age value: {cookie['max-age']}")
    print()
