from universal_coder.reliability import RetryPolicy, classify_error

def test_transient_errors_are_retryable():
    assert classify_error('connection reset by peer') == ('transient', True)
    assert classify_error('permission denied') == ('policy', False)

def test_retry_backoff_is_bounded():
    p=RetryPolicy(max_attempts=4, base_delay=1, max_delay=3)
    assert [p.delay(i) for i in range(1,4)] == [1,2,3]
