from django.http import HttpResponse
from django.test import RequestFactory

from waffle.middleware import WaffleMiddleware
from waffle.defaults import MAX_AGE


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


def test_rollout_cookies_all_combinations():
    # Test all four combinations:
    # (active=True, session_only=True): max-age should be None (session cookie)
    # (active=False, session_only=True): max-age should be None
    # (active=True, session_only=False): max-age should be MAX_AGE
    # (active=False, session_only=False): max-age should be MAX_AGE
    get.waffles = {
        'active_true_session_true': [True, True],
        'active_false_session_true': [False, True],
        'active_true_session_false': [True, False],
        'active_false_session_false': [False, False],
    }
    resp = HttpResponse()
    resp = WaffleMiddleware().process_response(get, resp)
    
    for k in get.waffles:
        cookie = f'dwf_{k}'
        active, session_only = get.waffles[k]
        assert cookie in resp.cookies
        assert str(active) == resp.cookies[cookie].value
        
        if session_only:
            # Session cookie: max-age should not be set or should be empty
            assert 'max-age' not in resp.cookies[cookie] or not resp.cookies[cookie]['max-age']
        else:
            # Persistent cookie: max-age should be set
            assert resp.cookies[cookie]['max-age']
            assert int(resp.cookies[cookie]['max-age']) == MAX_AGE


def test_rollout_cookies():
    get.waffles = {'foo': [True, False],
                   'bar': [False, True],
                   'baz': [True, False],
                   'qux': [False, False]}
    resp = HttpResponse()
    resp = WaffleMiddleware().process_response(get, resp)
    for k in get.waffles:
        cookie = f'dwf_{k}'
        assert cookie in resp.cookies
        assert str(get.waffles[k][0]) == resp.cookies[cookie].value
        if get.waffles[k][1]:
            assert 'max-age' not in resp.cookies[cookie] or not bool(resp.cookies[cookie]['max-age'])
        else:
            assert resp.cookies[cookie]['max-age']


def test_testing_cookies():
    get.waffles = {}
    get.waffle_tests = {'foo': True, 'bar': False}
    resp = HttpResponse()
    resp = WaffleMiddleware().process_response(get, resp)
    for k in get.waffle_tests:
        cookie = f'dwft_{k}'
        assert str(get.waffle_tests[k]) == resp.cookies[cookie].value
        assert not resp.cookies[cookie]['max-age']
