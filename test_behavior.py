#!/usr/bin/env python
from django.http import HttpResponse, HttpRequest
from waffle.middleware import WaffleMiddleware

# Create a mock request
request = HttpRequest()
request.waffles = {
    'case1': [True, True],   # active=True, rollout=True
    'case2': [False, True],  # active=False, rollout=True
    'case3': [True, False],  # active=True, rollout=False
    'case4': [False, False], # active=False, rollout=False
}

# Create a response
response = HttpResponse()

# Process with middleware
response = WaffleMiddleware().process_response(request, response)

# Print results
print("Testing cookie max_age behavior for all four combinations:")
print("="*70)

for name in ['case1', 'case2', 'case3', 'case4']:
    cookie_name = f'dwf_{name}'
    cookie = response.cookies[cookie_name]
    active, rollout = request.waffles[name]
    max_age = cookie.get('max-age', 'Not set')
    print(f"{name}: active={active}, rollout={rollout}")
    print(f"  Cookie value: {cookie.value}")
    print(f"  max-age: {max_age}")
    print()
