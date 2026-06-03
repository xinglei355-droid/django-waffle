from contextlib import ExitStack
from unittest import mock

from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase, override_settings

from waffle import (
    get_waffle_flag_model,
    get_waffle_sample_model,
    get_waffle_switch_model,
)
from waffle.utils import get_setting


class ModelsTests(TestCase):
    def test_natural_keys(self):
        flag = get_waffle_flag_model().objects.create(name='test-flag')
        switch = get_waffle_switch_model().objects.create(name='test-switch')
        sample = get_waffle_sample_model().objects.create(name='test-sample', percent=0)

        self.assertEqual(flag.natural_key(), ('test-flag',))
        self.assertEqual(switch.natural_key(), ('test-switch',))
        self.assertEqual(sample.natural_key(), ('test-sample',))

        self.assertEqual(
            get_waffle_flag_model().objects.get_by_natural_key("test-flag"), flag
        )
        self.assertEqual(
            get_waffle_switch_model().objects.get_by_natural_key("test-switch"), switch
        )
        self.assertEqual(
            get_waffle_sample_model().objects.get_by_natural_key("test-sample"), sample
        )

    def test_flag_is_not_active_for_none_requests(self):
        flag = get_waffle_flag_model().objects.create(name='test-flag')
        self.assertEqual(flag.is_active(None), False)

    def test_is_active_for_user_when_everyone_is_active(self):
        flag = get_waffle_flag_model().objects.create(name='test-flag')
        flag.everyone = True
        self.assertEqual(flag.is_active_for_user(User()), True)

    def test_is_active_table_driven(self):
        def make_request(*, query=None, user=None, cookies=None, headers=None, language=None):
            request = RequestFactory().get('/foo', data=query or {}, **(headers or {}))
            request.user = user if user is not None else AnonymousUser()
            if cookies:
                request.COOKIES.update(cookies)
            if language is not None:
                request.LANGUAGE_CODE = language
            return request

        test_cookie = get_setting('TEST_COOKIE')
        flag_model = get_waffle_flag_model()
        cases = [
            {
                'name': 'override-query',
                'settings': {'WAFFLE_OVERRIDE': True},
                'flag_kwargs': {'everyone': False},
                'request_factory': lambda name: make_request(query={name: '1'}),
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'testing-query',
                'flag_kwargs': {'testing': True},
                'request_factory': lambda name: make_request(query={test_cookie % name: '1'}),
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': {'testing-query': True},
            },
            {
                'name': 'testing-header',
                'flag_kwargs': {'testing': True},
                'request_factory': lambda name: make_request(
                    cookies={test_cookie % name: 'True'},
                    headers={f'HTTP_{(test_cookie % name).upper().replace("-", "_")}': '0'},
                ),
                'expected': False,
                'expected_waffles': None,
                'expected_waffle_tests': {'testing-header': False},
            },
            {
                'name': 'testing-cookie',
                'flag_kwargs': {'testing': True},
                'request_factory': lambda name: make_request(cookies={test_cookie % name: 'True'}),
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'language-hit',
                'flag_kwargs': {'languages': 'fr,es'},
                'request_factory': lambda name: make_request(language='fr'),
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'authenticated-hit',
                'flag_kwargs': {'authenticated': True, 'superusers': False},
                'request_factory': lambda name: make_request(user=User()),
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'staff-hit',
                'flag_kwargs': {'staff': True, 'superusers': False},
                'request_factory': lambda name: make_request(user=User(is_staff=True)),
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'superuser-hit',
                'flag_kwargs': {'superusers': True},
                'request_factory': lambda name: make_request(user=User(is_superuser=True)),
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'percent-hit',
                'flag_kwargs': {'percent': '50.0'},
                'request_factory': lambda name: make_request(),
                'patch_random': 1,
                'expected': True,
                'expected_waffles': {'percent-hit': [True, False]},
                'expected_waffle_tests': None,
            },
            {
                'name': 'default-false',
                'flag_kwargs': {'superusers': False},
                'request_factory': lambda name: make_request(),
                'expected': False,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
        ]

        for case in cases:
            with self.subTest(case=case['name']):
                with ExitStack() as stack:
                    if 'settings' in case:
                        stack.enter_context(override_settings(**case['settings']))
                    if 'patch_random' in case:
                        stack.enter_context(
                            mock.patch(
                                'waffle.models.random.uniform',
                                return_value=case['patch_random'],
                            )
                        )

                    flag = flag_model.objects.create(
                        name=case['name'],
                        **case['flag_kwargs'],
                    )
                    request = case['request_factory'](flag.name)

                    self.assertEqual(flag.is_active(request), case['expected'])

                    if case['expected_waffles'] is None:
                        self.assertFalse(hasattr(request, 'waffles'))
                    else:
                        self.assertEqual(request.waffles, case['expected_waffles'])

                    if case['expected_waffle_tests'] is None:
                        self.assertFalse(hasattr(request, 'waffle_tests'))
                    else:
                        self.assertEqual(request.waffle_tests, case['expected_waffle_tests'])
