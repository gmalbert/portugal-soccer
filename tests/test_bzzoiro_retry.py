from unittest.mock import Mock

import pytest
import requests

from scripts.bzzoiro_retry import retry_connection_errors


def test_retries_connection_reset_and_returns_result(monkeypatch):
    sleep = Mock()
    monkeypatch.setattr("scripts.bzzoiro_retry.time.sleep", sleep)
    operation = Mock(side_effect=[requests.ConnectionError("reset"), {"id": 1}])
    assert retry_connection_errors(operation, 42, status="open") == {"id": 1}
    assert operation.call_count == 2
    operation.assert_called_with(42, status="open")
    sleep.assert_called_once_with(1)


def test_retries_are_bounded_and_failure_propagates(monkeypatch):
    sleep = Mock()
    monkeypatch.setattr("scripts.bzzoiro_retry.time.sleep", sleep)
    operation = Mock(side_effect=requests.Timeout("timeout"))
    with pytest.raises(requests.Timeout):
        retry_connection_errors(operation)
    assert operation.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [1, 2]


def test_nontransient_failure_is_not_retried(monkeypatch):
    sleep = Mock()
    monkeypatch.setattr("scripts.bzzoiro_retry.time.sleep", sleep)
    operation = Mock(side_effect=ValueError("invalid data"))
    with pytest.raises(ValueError):
        retry_connection_errors(operation)
    operation.assert_called_once()
    sleep.assert_not_called()
