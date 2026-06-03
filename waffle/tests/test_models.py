from django.test import TestCase

from waffle import (
    get_waffle_flag_model,
    get_waffle_sample_model,
    get_waffle_switch_model,
)
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


class CacheHelperTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.FlagModel = get_waffle_flag_model()
        cls.SwitchModel = get_waffle_switch_model()
        cls.SampleModel = get_waffle_sample_model()

    def test_get_or_set_cache_hit_returns_cached_value(self):
        flag = self.FlagModel.objects.create(name='test-flag')

        flag2 = self.FlagModel.get('test-flag')
        self.assertEqual(flag.pk, flag2.pk)
        self.assertEqual(flag.name, flag2.name)

        flag3 = self.FlagModel.get('test-flag')
        self.assertEqual(flag.pk, flag3.pk)

    def test_get_or_set_cache_empty_sentinel_returns_stub(self):
        result = self.FlagModel.get('nonexistent')
        self.assertIsNone(result.pk)
        self.assertEqual(result.name, 'nonexistent')

    def test_get_or_set_cache_empty_sentinel_returns_empty_list(self):
        self.FlagModel.objects.all().delete()
        result = self.FlagModel.get_all()
        self.assertEqual(result, [])

    def test_get_or_set_cache_db_read_for_get(self):
        flag = self.FlagModel.objects.create(name='db-read-flag')
        self.FlagModel.get('db-read-flag')

        result = self.FlagModel.get('db-read-flag')
        self.assertEqual(flag.pk, result.pk)
        self.assertEqual(flag.name, result.name)

    def test_get_or_set_cache_db_read_for_get_all(self):
        self.FlagModel.objects.all().delete()
        flag = self.FlagModel.objects.create(name='flag-a')

        result = self.FlagModel.get_all()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, 'flag-a')

    def test_switch_get_and_get_all_cache(self):
        switch = self.SwitchModel.objects.create(name='test-switch', active=True)

        result = self.SwitchModel.get('test-switch')
        self.assertEqual(switch.pk, result.pk)

        result2 = self.SwitchModel.get('test-switch')
        self.assertEqual(result2.pk, switch.pk)

        all_switches = self.SwitchModel.get_all()
        self.assertEqual(len(all_switches), 1)

    def test_sample_get_and_get_all_cache(self):
        sample = self.SampleModel.objects.create(name='test-sample', percent=50)

        result = self.SampleModel.get('test-sample')
        self.assertEqual(sample.pk, result.pk)

        result2 = self.SampleModel.get('test-sample')
        self.assertEqual(result2.pk, sample.pk)

        all_samples = self.SampleModel.get_all()
        self.assertEqual(len(all_samples), 1)

    def test_manager_create_invalidates_all_cache(self):
        self.FlagModel.objects.all().delete()

        self.FlagModel.objects.create(name='created-flag')
        all_flags = self.FlagModel.get_all()
        self.assertEqual(len(all_flags), 1)
        self.assertEqual(all_flags[0].name, 'created-flag')

    def test_get_nonexistent_switch_returns_stub(self):
        result = self.SwitchModel.get('no-such-switch')
        self.assertIsNone(result.pk)
        self.assertEqual(result.name, 'no-such-switch')

    def test_get_nonexistent_sample_returns_stub(self):
        result = self.SampleModel.get('no-such-sample')
        self.assertIsNone(result.pk)
        self.assertEqual(result.name, 'no-such-sample')
