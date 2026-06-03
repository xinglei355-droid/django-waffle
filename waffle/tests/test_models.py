from django.test import TestCase
from django.core import cache

from waffle import (
    get_waffle_flag_model,
    get_waffle_sample_model,
    get_waffle_switch_model,
)
from waffle.models import CACHE_EMPTY
from waffle.utils import get_setting, keyfmt
from django.contrib.auth.models import User


class CachePathTests(TestCase):
    def setUp(self):
        cache.cache.clear()

    def test_get_cache_hit(self):
        flag_model = get_waffle_flag_model()
        flag = flag_model.objects.create(name='test-flag')
        cache_key = flag_model._cache_key('test-flag')
        cache.cache.set(cache_key, flag)

        result = flag_model.get('test-flag')
        self.assertEqual(result.pk, flag.pk)
        self.assertEqual(result.name, 'test-flag')

    def test_get_db_read_then_cache(self):
        flag_model = get_waffle_flag_model()
        flag = flag_model.objects.create(name='test-flag')
        cache_key = flag_model._cache_key('test-flag')
        cache.cache.delete(cache_key)

        result = flag_model.get('test-flag')
        self.assertEqual(result.pk, flag.pk)
        self.assertEqual(result.name, 'test-flag')

        cached = cache.cache.get(cache_key)
        self.assertEqual(cached.pk, flag.pk)

    def test_get_missing_object_cached_empty(self):
        flag_model = get_waffle_flag_model()
        cache_key = flag_model._cache_key('nonexistent')
        cache.cache.delete(cache_key)

        result = flag_model.get('nonexistent')
        self.assertEqual(result.name, 'nonexistent')
        self.assertIsNone(result.pk)

        cached = cache.cache.get(cache_key)
        self.assertEqual(cached, CACHE_EMPTY)

    def test_get_empty_sentinel_from_cache(self):
        flag_model = get_waffle_flag_model()
        cache_key = flag_model._cache_key('nonexistent')
        cache.cache.set(cache_key, CACHE_EMPTY)

        result = flag_model.get('nonexistent')
        self.assertEqual(result.name, 'nonexistent')
        self.assertIsNone(result.pk)

    def test_get_all_cache_hit(self):
        flag_model = get_waffle_flag_model()
        flag_model.objects.create(name='flag1')
        flag_model.objects.create(name='flag2')
        cache_key = get_setting('ALL_FLAGS_CACHE_KEY')
        all_flags = list(flag_model.objects.all())
        cache.cache.set(cache_key, all_flags)

        result = flag_model.get_all()
        self.assertEqual(len(result), 2)
        self.assertEqual({f.name for f in result}, {'flag1', 'flag2'})

    def test_get_all_db_read_then_cache(self):
        flag_model = get_waffle_flag_model()
        flag_model.objects.create(name='flag1')
        flag_model.objects.create(name='flag2')
        cache_key = get_setting('ALL_FLAGS_CACHE_KEY')
        cache.cache.delete(cache_key)

        result = flag_model.get_all()
        self.assertEqual(len(result), 2)
        self.assertEqual({f.name for f in result}, {'flag1', 'flag2'})

        cached = cache.cache.get(cache_key)
        self.assertEqual(len(cached), 2)

    def test_get_all_empty_list_cached_empty(self):
        flag_model = get_waffle_flag_model()
        cache_key = get_setting('ALL_FLAGS_CACHE_KEY')
        cache.cache.delete(cache_key)

        result = flag_model.get_all()
        self.assertEqual(result, [])

        cached = cache.cache.get(cache_key)
        self.assertEqual(cached, CACHE_EMPTY)

    def test_get_all_empty_sentinel_from_cache(self):
        flag_model = get_waffle_flag_model()
        cache_key = get_setting('ALL_FLAGS_CACHE_KEY')
        cache.cache.set(cache_key, CACHE_EMPTY)

        result = flag_model.get_all()
        self.assertEqual(result, [])

    def test_switch_get_cache_hit(self):
        switch_model = get_waffle_switch_model()
        switch = switch_model.objects.create(name='test-switch', active=True)
        cache_key = switch_model._cache_key('test-switch')
        cache.cache.set(cache_key, switch)

        result = switch_model.get('test-switch')
        self.assertEqual(result.pk, switch.pk)

    def test_switch_get_missing_object_cached_empty(self):
        switch_model = get_waffle_switch_model()
        cache_key = switch_model._cache_key('nonexistent')
        cache.cache.delete(cache_key)

        result = switch_model.get('nonexistent')
        self.assertEqual(result.name, 'nonexistent')
        self.assertIsNone(result.pk)

        cached = cache.cache.get(cache_key)
        self.assertEqual(cached, CACHE_EMPTY)

    def test_sample_get_cache_hit(self):
        sample_model = get_waffle_sample_model()
        sample = sample_model.objects.create(name='test-sample', percent=50)
        cache_key = sample_model._cache_key('test-sample')
        cache.cache.set(cache_key, sample)

        result = sample_model.get('test-sample')
        self.assertEqual(result.pk, sample.pk)

    def test_sample_get_missing_object_cached_empty(self):
        sample_model = get_waffle_sample_model()
        cache_key = sample_model._cache_key('nonexistent')
        cache.cache.delete(cache_key)

        result = sample_model.get('nonexistent')
        self.assertEqual(result.name, 'nonexistent')
        self.assertIsNone(result.pk)

        cached = cache.cache.get(cache_key)
        self.assertEqual(cached, CACHE_EMPTY)

    def test_get_all_switches_cache_paths(self):
        switch_model = get_waffle_switch_model()
        cache_key = get_setting('ALL_SWITCHES_CACHE_KEY')
        cache.cache.delete(cache_key)

        result = switch_model.get_all()
        self.assertEqual(result, [])
        self.assertEqual(cache.cache.get(cache_key), CACHE_EMPTY)

        switch_model.objects.create(name='switch1')
        cache.cache.delete(cache_key)

        result = switch_model.get_all()
        self.assertEqual(len(result), 1)

    def test_get_all_samples_cache_paths(self):
        sample_model = get_waffle_sample_model()
        cache_key = get_setting('ALL_SAMPLES_CACHE_KEY')
        cache.cache.delete(cache_key)

        result = sample_model.get_all()
        self.assertEqual(result, [])
        self.assertEqual(cache.cache.get(cache_key), CACHE_EMPTY)

        sample_model.objects.create(name='sample1', percent=50)
        cache.cache.delete(cache_key)

        result = sample_model.get_all()
        self.assertEqual(len(result), 1)


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
