from django.http import HttpResponse
from django.test import RequestFactory, override_settings

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


@override_settings(WAFFLE_MAX_AGE=123)
def test_rollout_cookies():
    get.waffles = {'foo': [True, True],
                   'bar': [False, True],
                   'baz': [True, False],
                   'qux': [False, False]}
    resp = HttpResponse()
    resp = WaffleMiddleware().process_response(get, resp)

    assert resp.cookies['dwf_foo']['max-age'] == 123
    assert resp.cookies['dwf_bar']['max-age'] == ''
    assert resp.cookies['dwf_baz']['max-age'] == 123
    assert resp.cookies['dwf_qux']['max-age'] == 123


def test_testing_cookies():
    get.waffles = {}
    get.waffle_tests = {'foo': True, 'bar': False}
    resp = HttpResponse()
    resp = WaffleMiddleware().process_response(get, resp)
    for k in get.waffle_tests:
        cookie = f'dwft_{k}'
        assert str(get.waffle_tests[k]) == resp.cookies[cookie].value
        assert not resp.cookies[cookie]['max-age']
