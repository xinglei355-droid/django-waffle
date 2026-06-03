from django.http import HttpResponse
from django.test import RequestFactory

from waffle.middleware import WaffleMiddleware


get = RequestFactory().get('/foo')


def test_set_cookies():
    get.waffles = {'foo': [True, False], 'bar': [False, False]}
    resp = HttpResponse()
    assert 'dwf_foo' not in resp.cookies
    assert 'dwf_bar' not in resp.cookies

    resp = WaffleMiddleware().process_response(get, resp)
    assert 'dwf_foo' in resp.cookies
    assert 'dwf_bar' in resp.cookies

    assert 'True' == resp.cookies['dwf_foo'].value
    assert 'False' == resp.cookies['dwf_bar'].value


def test_rollout_cookies():
    get.waffles = {'foo': [True, True],
                   'bar': [False, True],
                   'baz': [True, False],
                   'qux': [False, False]}
    resp = HttpResponse()
    resp = WaffleMiddleware().process_response(get, resp)
    for k in get.waffles:
        cookie = f'dwf_{k}'
        assert cookie in resp.cookies
        assert str(get.waffles[k][0]) == resp.cookies[cookie].value
        if get.waffles[k][0]:
            assert resp.cookies[cookie]['max-age']
        else:
            assert not resp.cookies[cookie]['max-age']


def test_cookie_max_age_all_combinations():
    """Verify cookie max_age for all four combinations of active and rollout."""
    from waffle.defaults import MAX_AGE

    get.waffles = {
        'active_rollout': [True, True],
        'inactive_rollout': [False, True],
        'active_no_rollout': [True, False],
        'inactive_no_rollout': [False, False],
    }
    resp = HttpResponse()
    resp = WaffleMiddleware().process_response(get, resp)

    for key, (active, rollout) in get.waffles.items():
        cookie = f'dwf_{key}'
        assert cookie in resp.cookies
        assert str(active) == resp.cookies[cookie].value

        if active:
            assert resp.cookies[cookie]['max-age'] == MAX_AGE
        else:
            assert not resp.cookies[cookie]['max-age']


def test_testing_cookies():
    get.waffles = {}
    get.waffle_tests = {'foo': True, 'bar': False}
    resp = HttpResponse()
    resp = WaffleMiddleware().process_response(get, resp)
    for k in get.waffle_tests:
        cookie = f'dwft_{k}'
        assert str(get.waffle_tests[k]) == resp.cookies[cookie].value
        assert not resp.cookies[cookie]['max-age']
