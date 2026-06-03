import random
from unittest import mock

from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings

from waffle import (
    get_waffle_flag_model,
    get_waffle_sample_model,
    get_waffle_switch_model,
)


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
        flag_model = get_waffle_flag_model()

        test_cases = [
            {
                'name': 'OVERRIDE query param (1) → True',
                'flag_kwargs': {'name': 'override-on'},
                'settings': {'WAFFLE_OVERRIDE': True},
                'query': {'override-on': '1'},
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'OVERRIDE query param (0) → False',
                'flag_kwargs': {'name': 'override-off'},
                'settings': {'WAFFLE_OVERRIDE': True},
                'query': {'override-off': '0'},
                'expected': False,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'testing query param (1) → True, waffle_tests set',
                'flag_kwargs': {'name': 'tq-flag', 'testing': True},
                'query': {'dwft_tq-flag': '1'},
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': {'tq-flag': True},
            },
            {
                'name': 'testing query param (0) → False, waffle_tests set',
                'flag_kwargs': {'name': 'tq-off', 'testing': True},
                'query': {'dwft_tq-off': '0'},
                'expected': False,
                'expected_waffles': None,
                'expected_waffle_tests': {'tq-off': False},
            },
            {
                'name': 'testing header (1) → True, waffle_tests set',
                'flag_kwargs': {'name': 'th-flag', 'testing': True},
                'headers': {'DWFT_TH_FLAG': '1'},
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': {'th-flag': True},
            },
            {
                'name': 'testing cookie (True) → True, no waffle_tests',
                'flag_kwargs': {'name': 'tc-flag', 'testing': True},
                'cookies': {'dwft_tc-flag': 'True'},
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'testing cookie (False) → False, no waffle_tests',
                'flag_kwargs': {'name': 'tc-off', 'testing': True},
                'cookies': {'dwft_tc-off': 'False'},
                'expected': False,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'testing disabled → False, no waffle_tests',
                'flag_kwargs': {'name': 'td-flag'},
                'query': {'dwft_td-flag': '1'},
                'expected': False,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'language hit → True',
                'flag_kwargs': {'name': 'lang-hit', 'languages': 'en,fr'},
                'language_code': 'en',
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'language miss → False',
                'flag_kwargs': {'name': 'lang-miss', 'languages': 'en,fr'},
                'language_code': 'de',
                'expected': False,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'authenticated hit → True',
                'flag_kwargs': {'name': 'auth-hit', 'authenticated': True},
                'user': User(username='testuser'),
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'staff hit → True',
                'flag_kwargs': {'name': 'staff-hit', 'staff': True},
                'user': User(username='staffuser', is_staff=True),
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'superuser hit → True',
                'flag_kwargs': {'name': 'su-hit', 'superusers': True},
                'user': User(username='admin', is_superuser=True),
                'expected': True,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
            {
                'name': 'percent hit → True, waffles set',
                'flag_kwargs': {'name': 'pct-hit', 'percent': 50.0},
                'mock_uniform': 10.0,
                'expected': True,
                'expected_waffles': {'pct-hit': [True, False]},
                'expected_waffle_tests': None,
            },
            {
                'name': 'percent miss → False, waffles set',
                'flag_kwargs': {'name': 'pct-miss', 'percent': 50.0},
                'mock_uniform': 70.0,
                'expected': False,
                'expected_waffles': {'pct-miss': [False, False]},
                'expected_waffle_tests': None,
            },
            {
                'name': 'default False',
                'flag_kwargs': {'name': 'default-false'},
                'expected': False,
                'expected_waffles': None,
                'expected_waffle_tests': None,
            },
        ]

        for case in test_cases:
            with self.subTest(case['name']):
                flag = flag_model.objects.create(**case['flag_kwargs'])

                headers = {}
                for k, v in case.get('headers', {}).items():
                    headers['HTTP_{}'.format(k)] = v

                request = RequestFactory().get(
                    '/foo', data=case.get('query', {}), **headers
                )

                request.user = case.get('user', AnonymousUser())

                if 'cookies' in case:
                    request.COOKIES = case['cookies']

                if 'language_code' in case:
                    request.LANGUAGE_CODE = case['language_code']

                mock_uniform = case.get('mock_uniform')
                settings_override = case.get('settings', {})

                if mock_uniform is not None:
                    with mock.patch.object(
                        random, 'uniform', return_value=mock_uniform
                    ):
                        with override_settings(**settings_override):
                            result = flag.is_active(request)
                else:
                    with override_settings(**settings_override):
                        result = flag.is_active(request)

                self.assertEqual(case['expected'], result)

                if case['expected_waffles'] is not None:
                    self.assertTrue(hasattr(request, 'waffles'))
                    self.assertEqual(
                        case['expected_waffles'], request.waffles
                    )
                else:
                    self.assertFalse(hasattr(request, 'waffles'))

                if case['expected_waffle_tests'] is not None:
                    self.assertTrue(hasattr(request, 'waffle_tests'))
                    self.assertEqual(
                        case['expected_waffle_tests'],
                        request.waffle_tests,
                    )
                else:
                    self.assertFalse(hasattr(request, 'waffle_tests'))
