from server import *
from helpers import *

import requests
import json
import pytest
from unittest import mock
import requests_mock

SHOPIFY_API_KEY = os.environ.get('SHOPIFY_API_KEY')
INSTALL_REDIRECT_URL = os.environ.get('INSTALL_REDIRECT_URL')
APP_NAME = os.environ.get('APP_NAME')

def test_install_redirect_url():
  cookie = uuid.uuid4().hex
  shop = "myfirstdevstor.myshopify.com"
  scopes = ','.join(['write_script_tags'])
  access_modes = ','.join([])
  assert generate_install_redirect_url("myfirstdevstor.myshopify.com", ['write_script_tags'], cookie, []) == f"https://{shop}/admin/oauth/authorize?client_id={SHOPIFY_API_KEY}&scope={scopes}&redirect_uri={INSTALL_REDIRECT_URL}&state={cookie}&grant_options[]={access_modes}"

def test_post_install_redirect_url():
  shop = "myfirstdevstor.myshopify.com"
  assert generate_post_install_redirect_url(shop) ==  f"https://{shop}/admin/apps/{APP_NAME}"

def test_verify_hmac():
  hmac = 'e0b39335914db74251058808392504999c43d90a8b25cc9ffc9fa4334d1c3ab2'
  data = b'host=YWRtaW4uc2hvcGlmeS5jb20vc3RvcmUvbXlmaXJzdGRldnN0b3I&shop=myfirstdevstor.myshopify.com&timestamp=1712241130'
  assert verify_hmac(data, hmac) == True

def test_is_valid_shop():
    valid_storename = "mydevstor.myshopify.com"
    assert is_valid_shop(valid_storename) == True

def test_req_launch():
  with requests_mock.Mocker() as m:
    url = 'https://mocked-url/app_launched'
    m.get(url=f"{url}", status_code= 302)
    resp = requests.get(url=f"{url}", params={
       "hmac": "08546ef8caa82e4157e07025613e2feaa11c49a6778d28418239100b8c83f3dc",
       "host": "YWRtaW4uc2hvcGlmeS5jb20vc3RvcmUvbXlmaXJzdGRldnN0b3I",
       "shop": "myfirstdevstor.myshopify.com",
       "timestamp": 1712164023
    })
    assert m.last_request.qs["hmac"] == ["08546ef8caa82e4157e07025613e2feaa11c49a6778d28418239100b8c83f3dc"]
    assert m.last_request.qs["host"] == ["YWRtaW4uc2hvcGlmeS5jb20vc3RvcmUvbXlmaXJzdGRldnN0b3I".lower()]
    assert m.last_request.qs["shop"] == ["myfirstdevstor.myshopify.com"]
    assert m.last_request.qs["timestamp"] == ["1712164023"]
    assert resp.status_code == 302

def test_req_app_installed():
  with requests_mock.Mocker() as m:
    url = 'https://mocked-url/app_installed'
    nonce = uuid.uuid4().hex
    m.get(url=f"{url}", status_code= 302)
    resp = requests.get(url=f"{url}", params={
       "code": "c03a6c79-b967-4e5d-8ec0-60215dd2e275",
       "hmac": "08546ef8caa82e4157e07025613e2feaa11c49a6778d28418239100b8c83f3dc",
       "state": nonce,
       "host": "YWRtaW4uc2hvcGlmeS5jb20vc3RvcmUvbXlmaXJzdGRldnN0b3I",
       "shop": "myfirstdevstor.myshopify.com",
       "timestamp": 1712164023
    })
    assert m.last_request.qs["hmac"] == ["08546ef8caa82e4157e07025613e2feaa11c49a6778d28418239100b8c83f3dc"]
    assert m.last_request.qs["host"] == ["YWRtaW4uc2hvcGlmeS5jb20vc3RvcmUvbXlmaXJzdGRldnN0b3I".lower()]
    assert m.last_request.qs["shop"] == ["myfirstdevstor.myshopify.com"]
    assert m.last_request.qs["code"] == ["c03a6c79-b967-4e5d-8ec0-60215dd2e275"]
    assert m.last_request.qs["state"] == [nonce]
    assert m.last_request.qs["timestamp"] == [str(1712164023)]
    assert resp.status_code == 302


def test_req_app_uninstalled():
  with requests_mock.Mocker() as m:
    url = 'https://mocked-url/app_uninstalled'
    m.get(url=f"{url}", status_code= 200)
    resp = requests.get(url=f"{url}")
    assert resp.status_code == 200
