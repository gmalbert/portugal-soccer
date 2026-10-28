"""Retry transient Bzzoiro connection failures without hiding bad data."""

import time

import requests


def retry_connection_errors(operation, *args, **kwargs):
    """Retry connection errors and timeouts twice, then propagate the failure."""
    for attempt in range(3):
        try:
            return operation(*args, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt == 2:
                raise
            delay = 2 ** attempt
            print(f"Bzzoiro connection failed; retrying in {delay}s", flush=True)
            time.sleep(delay)
