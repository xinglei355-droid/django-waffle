#!/usr/bin/env python
"""Verify that our fixes work correctly."""

import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath('/app/django-waffle'))

from unittest.mock import Mock, MagicMock
from django.http import HttpResponse, HttpRequest
from django.conf import settings

# Configure minimal Django settings
if not settings.configured:
    settings.configure(
        DEBUG=True,
        WAFFLE_COOKIE='dwf_%s',
        WAFFLE_MAX_AGE=2592000,
        WAFFLE_SECURE=True,
    )

from waffle.middleware import WaffleMiddleware
from waffle.models import set_flag

print("Testing our fixes...")
print("="*80)

print("\n1. Testing WaffleMiddleware with session_only values:")

# Test all four combinations
test_cases = [
    ("active=True, session_only=True", True, True, None),
    ("active=False, session_only=True", False, True, None),
    ("active=True, session_only=False", True, False, 2592000),
    ("active=False, session_only=False", False, False, 2592000),
]

all_passed = True

for desc, active, session_only, expected_max_age in test_cases:
    request = HttpRequest()
    request.waffles = {'test': (active, session_only)}
    response = HttpResponse()
    
    response = WaffleMiddleware().process_response(request, response)
    
    cookie = response.cookies['dwf_test']
    actual_max_age = cookie.get('max-age')
    
    if actual_max_age == '':
        actual_max_age = None
    elif actual_max_age is not None:
        actual_max_age = int(actual_max_age)
    
    passed = (cookie.value == str(active)) and (actual_max_age == expected_max_age)
    
    print(f"\n{desc}:")
    print(f"  Cookie value: {cookie.value} (expected: {str(active)})")
    print(f"  max-age: {actual_max_age} (expected: {expected_max_age})")
    print(f"  {'✓ PASSED' if passed else '✗ FAILED'}")
    
    if not passed:
        all_passed = False

print("\n" + "="*80)

print("\n2. Testing set_flag function:")
request2 = HttpRequest()
set_flag(request2, 'test_flag', True, False)
print(f"set_flag('test_flag', True, False): {request2.waffles['test_flag']}")
assert request2.waffles['test_flag'] == [True, False]

set_flag(request2, 'test_flag2', False, True)
print(f"set_flag('test_flag2', False, True): {request2.waffles['test_flag2']}")
assert request2.waffles['test_flag2'] == [False, True]
print("✓ set_flag tests passed")

print("\n" + "="*80)

if all_passed:
    print("\n🎉 All tests passed! Our fixes are correct.")
else:
    print("\n⚠️ Some tests failed.")
    sys.exit(1)
