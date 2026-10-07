"""Regressões offline da Issue #51: persistência, interrupções e retentativas."""

import json
import sqlite3
from unittest.mock import Mock

import pytest
import requests

from api_client import GitHubClient


def response(status=200, data=None, headers=None, raw=None):
    result = requests.Response()
    result.status_code = status
    result.headers.update(headers or {})
    result._content = raw if raw is not None else json.dumps(data if data is not None else {}).encode()
    return result


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Fails immediately if a regression accidentally attempts a real request.
    monkeypatch.setattr(requests.Session, "send", Mock(side_effect=AssertionError("Rede proibida nos testes")))
    return GitHubClient(token="fixture-token-only", cache_db_path=str(tmp_path / "cache.db"), max_retries=2)


@pytest.fixture
def sleeps(monkeypatch):
    sleep = Mock()
    monkeypatch.setattr("api_client.time.sleep", sleep)
    monkeypatch.setattr("api_client.time.time", lambda: 1000.0)
    return sleep


def cache_rows(client):
    connection = sqlite3.connect(client.cache_db_path)
    try:
        return connection.execute("SELECT cache_key, state, response_json FROM api_cache ORDER BY cache_key").fetchall()
    finally:
        connection.close()


def test_success_committed_before_interrupted_rate_limit_sleep(client, sleeps, monkeypatch):
    client.session.get = Mock(return_value=response(data=[{"id": 1}], headers={
        "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1010",
    }))

    def interrupt(_delay):
        assert cache_rows(client)[0][1] == "complete"
        raise KeyboardInterrupt

    sleeps.side_effect = interrupt
    with pytest.raises(KeyboardInterrupt):
        client.request("/runs", {"page": 1})
    sleeps.assert_called_once_with(13.0)

    restarted = GitHubClient(token="fixture-token-only", cache_db_path=client.cache_db_path)
    restarted.session.get = Mock(side_effect=AssertionError("Página completa não deve repetir rede"))
    assert restarted.request("/runs", {"page": 1})[1] == [{"id": 1}]
    restarted.session.get.assert_not_called()
    assert sleeps.call_count == 1


def test_paginate_resumes_pending_page_and_then_uses_only_cache(client, sleeps):
    client.max_retries = 0
    next_url = "https://api.github.com/runs?page=2"
    client.session.get = Mock(side_effect=[
        response(data={"items": [{"id": 1}]}, headers={"Link": f'<{next_url}>; rel="next"'}),
        response(status=503),
    ])
    with pytest.raises(RuntimeError, match="503"):
        client.paginate("/runs", {"page": 1})
    assert [row[1] for row in cache_rows(client)] == ["complete", "pending"]

    restarted = GitHubClient(token="fixture-token-only", cache_db_path=client.cache_db_path)
    restarted.session.get = Mock(return_value=response(data={"items": [{"id": 2}]}))
    expected = [{"id": 1}, {"id": 2}]
    assert restarted.paginate("/runs", {"page": 1}) == expected
    restarted.session.get.assert_called_once_with(next_url, params=None, verify=True, timeout=30)
    restarted.session.get.reset_mock()
    assert restarted.paginate("/runs", {"page": 1}) == expected
    restarted.session.get.assert_not_called()


@pytest.mark.parametrize("raw", [b"not json", b'"not an object"', b"null", b'{"incomplete_results": true}'])
def test_invalid_success_json_stays_pending_then_can_resume(client, sleeps, raw):
    client.session.get = Mock(side_effect=[response(raw=raw), response(data={"items": []})])
    with pytest.raises(ValueError):
        client.request("/runs")
    assert cache_rows(client)[0][1:] == ("pending", None)
    assert client.request("/runs")[1] == {"items": []}
    assert client.session.get.call_count == 2
    assert cache_rows(client)[0][1] == "complete"


@pytest.mark.parametrize("headers, expected", [
    ({"Retry-After": "7"}, 10.0),
    ({"retry-after": "Thu, 01 Jan 1970 00:16:47 GMT"}, 10.0),
    ({"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1012"}, 15.0),
    ({}, 1.0),
    ({"Retry-After": "invalid", "X-RateLimit-Remaining": "invalid"}, 1.0),
])
def test_http_429_retries_regardless_of_body(client, sleeps, headers, expected):
    client.session.get = Mock(side_effect=[response(429, headers=headers, raw=b"Try again"), response(data=[])])
    assert client.request("/runs")[1] == []
    sleeps.assert_called_once_with(expected)
    assert client.session.get.call_count == 2


def test_http_403_rate_limit_uses_headers_independent_of_message(client, sleeps):
    client.session.get = Mock(side_effect=[
        response(403, {"message": "Please wait"}, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1005"}),
        response(data=[]),
    ])
    assert client.request("/runs")[0] == 200
    sleeps.assert_called_once_with(8.0)


@pytest.mark.parametrize("status", [403, 404])
def test_non_retryable_http_error_does_not_complete_cache(client, sleeps, status):
    client.session.get = Mock(return_value=response(status, {"message": "Not available"}))
    assert client.request("/runs")[0] == status
    assert cache_rows(client)[0][1] == "pending"
    assert client.session.get.call_count == 1
    sleeps.assert_not_called()


def test_connection_and_5xx_retry_with_bounded_backoff(client, sleeps):
    client.max_retries = 3
    client.backoff_base_seconds = 40
    client.session.get = Mock(side_effect=[
        requests.ConnectionError("offline"), response(502), response(503), response(data=[]),
    ])
    assert client.request("/runs")[0] == 200
    assert [call.args[0] for call in sleeps.call_args_list] == [40, 60.0, 60.0]


def test_503_respeita_retry_after(client, sleeps):
    client.session.get = Mock(side_effect=[
        response(503, headers={"Retry-After": "15"}), response(data=[]),
    ])
    assert client.request("/runs")[0] == 200
    sleeps.assert_called_once_with(18.0)


@pytest.mark.parametrize("failure", [response(503), response(429), requests.ConnectionError("offline")])
def test_exhausted_retries_raise_and_leave_pending(client, sleeps, failure):
    client.session.get = Mock(side_effect=[failure, failure, failure])
    with pytest.raises(RuntimeError):
        client.request("/runs")
    assert client.session.get.call_count == 3
    assert sleeps.call_count == 2
    assert cache_rows(client)[0][1] == "pending"


def test_cache_storage_failure_propagates_before_wait(client, sleeps, monkeypatch):
    client.session.get = Mock(return_value=response(data=[], headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1010"}))
    monkeypatch.setattr(client, "_save_to_cache", Mock(side_effect=sqlite3.OperationalError("disk full")))
    with pytest.raises(sqlite3.OperationalError, match="disk full"):
        client.request("/runs")
    sleeps.assert_not_called()
    assert cache_rows(client)[0][1] == "pending"


def test_cache_invalidation_for_bad_collection_schema(client):
    client.session.get = Mock(side_effect=[response(data={"unexpected": True}), response(data=[])])
    with pytest.raises(ValueError, match="lista"):
        client.paginate("/runs")
    assert cache_rows(client)[0][1] == "pending"
    assert client.paginate("/runs") == []


def test_paginate_does_not_return_partial_items_after_http_failure(client):
    client.session.get = Mock(side_effect=[
        response(data=[{"id": 1}], headers={"Link": '<https://api.github.com/runs?page=2>; rel="next"'}),
        response(403, {"message": "Forbidden"}),
    ])
    with pytest.raises(RuntimeError, match="Paginação incompleta"):
        client.paginate("/runs")


def test_cached_credentials_absent_and_tls_enabled(client):
    client.session.get = Mock(return_value=response(data=[], headers={"Authorization": "fixture-token-only", "Link": ""}))
    client.request("/runs")
    assert client.session.get.call_args.kwargs["verify"] is True
    connection = sqlite3.connect(client.cache_db_path)
    try:
        dump = "\n".join(connection.iterdump())
    finally:
        connection.close()
    assert "fixture-token-only" not in dump
    assert "Authorization" not in dump
    assert "Bearer" not in dump


def test_old_cache_migration_marks_unvalidated_rows_pending(tmp_path):
    db = str(tmp_path / "old-cache.db")
    connection = sqlite3.connect(db)
    try:
        connection.execute("CREATE TABLE api_cache (cache_key TEXT PRIMARY KEY, url TEXT, status_code INTEGER, response_json TEXT, response_headers TEXT, timestamp REAL)")
        connection.execute("INSERT INTO api_cache VALUES (?, ?, 200, ?, '{}', 0)",
                           ("https://api.github.com/runs", "https://api.github.com/runs", '"invalid old response"'))
        connection.commit()
    finally:
        connection.close()
    client = GitHubClient(token="fixture-token-only", cache_db_path=db)
    assert cache_rows(client)[0][1] == "pending"
    client.session.get = Mock(return_value=response(data=[]))
    assert client.request("/runs")[1] == []
    assert cache_rows(client)[0][1] == "complete"


def test_corrupt_complete_cache_is_refetched(client):
    client.session.get = Mock(return_value=response(data=[]))
    client.request("/runs")
    connection = sqlite3.connect(client.cache_db_path)
    try:
        connection.execute("UPDATE api_cache SET response_json = 'broken'")
        connection.commit()
    finally:
        connection.close()
    assert client.request("/runs")[1] == []
    assert client.session.get.call_count == 2


def test_no_cache_option_never_writes_response(client):
    client.session.get = Mock(return_value=response(data=[]))
    assert client.request("/runs", use_cache=False)[1] == []
    assert cache_rows(client) == []
