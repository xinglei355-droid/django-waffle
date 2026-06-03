from django.test import TestCase

from waffle import (
    get_waffle_flag_model,
    get_waffle_sample_model,
    get_waffle_switch_model,
)
from waffle.utils import get_cache
from django.contrib.auth.models import User


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


class CacheTests(TestCase):
    def setUp(self):
        self.cache = get_cache()
        self.Flag = get_waffle_flag_model()
        self.Switch = get_waffle_switch_model()
        self.Sample = get_waffle_sample_model()

    def tearDown(self):
        self.cache.clear()

    def test_get_missing_flag(self):
        flag = self.Flag.get('non-existent-flag')
        self.assertIsNotNone(flag)
        self.assertEqual(flag.name, 'non-existent-flag')
        self.assertIsNone(flag.pk)

        cache_key = self.Flag._cache_key('non-existent-flag')
        self.assertEqual(self.cache.get(cache_key), '-')

    def test_get_existing_flag_from_db(self):
        flag = self.Flag.objects.create(name='existing-flag')
        
        result = self.Flag.get('existing-flag')
        self.assertEqual(result.pk, flag.pk)
        self.assertEqual(result.name, 'existing-flag')
        
        cache_key = self.Flag._cache_key('existing-flag')
        self.assertIsNotNone(self.cache.get(cache_key))

    def test_get_cached_flag(self):
        flag = self.Flag.objects.create(name='cached-flag')
        cache_key = self.Flag._cache_key('cached-flag')
        self.cache.set(cache_key, flag)
        
        result = self.Flag.get('cached-flag')
        self.assertEqual(result.pk, flag.pk)

    def test_get_all_empty_flags(self):
        flags = self.Flag.get_all()
        self.assertEqual(flags, [])
        
        cache_key = self.Flag.ALL_CACHE_KEY
        from waffle.utils import get_setting
        self.assertEqual(self.cache.get(get_setting(cache_key)), '-')

    def test_get_all_flags_from_db(self):
        flag1 = self.Flag.objects.create(name='flag1')
        flag2 = self.Flag.objects.create(name='flag2')
        
        flags = self.Flag.get_all()
        self.assertEqual(len(flags), 2)
        self.assertEqual({f.name for f in flags}, {'flag1', 'flag2'})

    def test_get_all_cached_flags(self):
        flag1 = self.Flag.objects.create(name='cached-flag1')
        flag2 = self.Flag.objects.create(name='cached-flag2')
        cache_key = self.Flag.ALL_CACHE_KEY
        from waffle.utils import get_setting
        self.cache.set(get_setting(cache_key), [flag1, flag2])
        
        flags = self.Flag.get_all()
        self.assertEqual(len(flags), 2)

    def test_switch_cache(self):
        switch = self.Switch.objects.create(name='test-switch', active=True)
        
        result = self.Switch.get('test-switch')
        self.assertEqual(result.pk, switch.pk)
        self.assertTrue(result.active)

    def test_sample_cache(self):
        sample = self.Sample.objects.create(name='test-sample', percent=50)
        
        result = self.Sample.get('test-sample')
        self.assertEqual(result.pk, sample.pk)
        self.assertEqual(result.percent, 50)

    def test_flag_user_ids_empty(self):
        flag = self.Flag.objects.create(name='user-flag')
        
        user_ids = flag._get_user_ids()
        self.assertEqual(user_ids, set())

    def test_flag_group_ids_empty(self):
        flag = self.Flag.objects.create(name='group-flag')
        
        group_ids = flag._get_group_ids()
        self.assertEqual(group_ids, set())
