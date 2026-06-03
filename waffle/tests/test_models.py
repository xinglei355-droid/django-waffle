from django.contrib.auth.models import User

from waffle import (
    get_waffle_flag_model,
    get_waffle_sample_model,
    get_waffle_switch_model,
)
from waffle.models import CACHE_EMPTY
from waffle.tests.base import TestCase
from waffle.utils import get_cache, get_setting


class ModelsTests(TestCase):
    def model_cases(self):
        return (
            ('flag', get_waffle_flag_model(), {}),
            ('switch', get_waffle_switch_model(), {}),
            ('sample', get_waffle_sample_model(), {'percent': 0}),
        )

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

    def test_get_returns_missing_object_and_caches_empty_sentinel(self):
        cache = get_cache()

        for label, model, _create_kwargs in self.model_cases():
            with self.subTest(model=label):
                missing = model.get('missing')

                self.assertEqual(missing.name, 'missing')
                self.assertIsNone(missing.pk)
                self.assertEqual(cache.get(model._cache_key('missing')), CACHE_EMPTY)

                with self.assertNumQueries(0):
                    cached_missing = model.get('missing')

                self.assertEqual(cached_missing.name, 'missing')
                self.assertIsNone(cached_missing.pk)

    def test_get_reads_from_database_and_caches_value(self):
        cache = get_cache()

        for label, model, create_kwargs in self.model_cases():
            with self.subTest(model=label):
                name = f'{label}-db'
                model.objects.create(name=name, **create_kwargs)

                with self.assertNumQueries(1):
                    cached_obj = model.get(name)

                self.assertEqual(cached_obj.name, name)
                self.assertEqual(cache.get(model._cache_key(name)).name, name)

    def test_get_all_returns_empty_list_and_caches_empty_sentinel(self):
        cache = get_cache()

        for label, model, _create_kwargs in self.model_cases():
            with self.subTest(model=label):
                self.assertEqual(model.get_all(), [])
                self.assertEqual(cache.get(get_setting(model.ALL_CACHE_KEY)), CACHE_EMPTY)

                with self.assertNumQueries(0):
                    self.assertEqual(model.get_all(), [])

    def test_get_and_get_all_use_cached_values_without_database_reads(self):
        cache = get_cache()

        for label, model, create_kwargs in self.model_cases():
            with self.subTest(model=label):
                name = f'{label}-cached'
                obj = model.objects.create(name=name, **create_kwargs)
                cache.set(model._cache_key(name), obj)
                cache.set(get_setting(model.ALL_CACHE_KEY), [obj])

                with self.assertNumQueries(0):
                    cached_obj = model.get(name)
                    cached_objs = model.get_all()

                self.assertEqual(cached_obj.name, name)
                self.assertEqual([cached.name for cached in cached_objs], [name])

    def test_create_invalidates_all_cache_and_get_all_reads_from_database(self):
        cache = get_cache()

        for label, model, create_kwargs in self.model_cases():
            with self.subTest(model=label):
                name = f'{label}-created'

                self.assertEqual(model.get_all(), [])
                self.assertEqual(cache.get(get_setting(model.ALL_CACHE_KEY)), CACHE_EMPTY)

                model.objects.create(name=name, **create_kwargs)

                self.assertIsNone(cache.get(get_setting(model.ALL_CACHE_KEY)))

                with self.assertNumQueries(1):
                    objs = model.get_all()

                self.assertEqual([obj.name for obj in objs], [name])
                self.assertEqual(
                    [obj.name for obj in cache.get(get_setting(model.ALL_CACHE_KEY))],
                    [name],
                )
