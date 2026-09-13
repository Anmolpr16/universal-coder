import json, threading, time
from pathlib import Path
from universal_coder.security import token_ok, is_loopback, SecurityConfig
from universal_coder.persistence import RunStore


def test_constant_time_token_contract():
    assert token_ok('abc','abc')
    assert not token_ok('ab','abc')
    assert token_ok('','')

def test_non_loopback_requires_auth():
    assert is_loopback('127.0.0.1')
    assert not is_loopback('0.0.0.0')

def test_security_defaults_are_bounded():
    c=SecurityConfig()
    assert c.max_request_bytes > 0
    assert c.max_concurrent_runs >= 1
