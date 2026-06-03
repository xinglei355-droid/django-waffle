from django.test import TestCase

from waffle import (
    get_waffle_flag_model,
    get_waffle_sample_model,
    get_waffle_switch_model,
)
from django.contrib.auth.models import User
from waffle.models import _cache_get_or_set, CACHE_EMPTY
from waffle.utils import get_cache

class CacheGetOrSetTests(TestCase):
    def setUp(self):
        self.cache = get_cache()
        self.cache.clear()
        
    def test_cache_miss_db_hit(self):
        # 数据库读取
        db_calls = []
        def fetch_db():
            db_calls.append(1)
            return 'db_value'
            
        res = _cache_get_or_set('my_key', fetch_db, empty_value='empty')
        self.assertEqual(res, 'db_value')
        self.assertEqual(len(db_calls), 1)
        self.assertEqual(self.cache.get('my_key'), 'db_value')
        
    def test_cache_hit(self):
        # 命中缓存
        self.cache.set('my_key', 'cached_value')
        db_calls = []
        def fetch_db():
            db_calls.append(1)
            return 'db_value'
            
        res = _cache_get_or_set('my_key', fetch_db, empty_value='empty')
        self.assertEqual(res, 'cached_value')
        self.assertEqual(len(db_calls), 0)

    def test_db_miss_caches_empty(self):
        # 缺失对象
        db_calls = []
        def fetch_db():
            db_calls.append(1)
            return None
            
        res = _cache_get_or_set('my_key', fetch_db, empty_value='empty')
        self.assertEqual(res, 'empty')
        self.assertEqual(len(db_calls), 1)
        self.assertEqual(self.cache.get('my_key'), CACHE_EMPTY)
        
        # Second call should hit cache and return empty_value without db call
        res2 = _cache_get_or_set('my_key', fetch_db, empty_value='empty')
        self.assertEqual(res2, 'empty')
        self.assertEqual(len(db_calls), 1)

    def test_db_returns_empty_list(self):
        # 空列表
        db_calls = []
        def fetch_db():
            db_calls.append(1)
            return []
            
        res = _cache_get_or_set('my_key', fetch_db, empty_value=[])
        self.assertEqual(res, [])
        self.assertEqual(len(db_calls), 1)
        self.assertEqual(self.cache.get('my_key'), CACHE_EMPTY)

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
