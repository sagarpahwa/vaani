"""
Unit tests for _sparql_client() and fetch_page() in utils/wikidata.py.
All network calls are mocked — no real Wikidata requests made.
"""
from unittest.mock import MagicMock, patch

import pytest

from utils.wikidata import _sparql_client, fetch_page, DELAY


class TestSparqlClient:
    def test_returns_sparql_wrapper_instance(self):
        client = _sparql_client()
        assert client is not None

    def test_uses_correct_endpoint(self):
        client = _sparql_client()
        assert "wikidata.org" in client.endpoint

    def test_sets_json_return_format(self):
        client = _sparql_client()
        # SPARQLWrapper stores returnFormat as an attribute
        assert client.returnFormat is not None


class TestFetchPage:
    def _make_binding(self):
        return {
            "item": {"value": "http://www.wikidata.org/entity/Q937"},
            "itemLabel": {"value": "Albert Einstein"},
            "wikiTitle": {"value": "Albert_Einstein"},
        }

    def test_returns_bindings_on_success(self):
        bindings = [self._make_binding()]
        mock_result = {"results": {"bindings": bindings}}

        with patch("utils.wikidata._sparql_client") as mock_client_fn, \
             patch("utils.wikidata.time.sleep"):
            mock_sparql = MagicMock()
            mock_sparql.query().convert.return_value = mock_result
            mock_client_fn.return_value = mock_sparql

            result = fetch_page("Q901", offset=0)

        assert result == bindings

    def test_returns_empty_list_when_no_results(self):
        mock_result = {"results": {"bindings": []}}

        with patch("utils.wikidata._sparql_client") as mock_client_fn, \
             patch("utils.wikidata.time.sleep"):
            mock_sparql = MagicMock()
            mock_sparql.query().convert.return_value = mock_result
            mock_client_fn.return_value = mock_sparql

            result = fetch_page("Q901", offset=0)

        assert result == []

    def test_uses_provided_offset(self):
        mock_result = {"results": {"bindings": []}}

        with patch("utils.wikidata._sparql_client") as mock_client_fn, \
             patch("utils.wikidata.time.sleep"):
            mock_sparql = MagicMock()
            mock_sparql.query().convert.return_value = mock_result
            mock_client_fn.return_value = mock_sparql

            fetch_page("Q901", offset=200)

            # Verify the query was set (contains the offset value)
            set_query_call = mock_sparql.setQuery.call_args[0][0]
            assert "200" in set_query_call

    def test_raises_on_non_429_http_error(self):
        import urllib.error

        with patch("utils.wikidata._sparql_client") as mock_client_fn, \
             patch("utils.wikidata.time.sleep"):
            mock_sparql = MagicMock()
            mock_sparql.query.side_effect = urllib.error.HTTPError(
                url="", code=500, msg="Server Error", hdrs={}, fp=None
            )
            mock_client_fn.return_value = mock_sparql

            with pytest.raises(urllib.error.HTTPError):
                fetch_page("Q901", offset=0, max_retries=1)

    def test_raises_after_max_retries_on_429(self):
        import urllib.error

        with patch("utils.wikidata._sparql_client") as mock_client_fn, \
             patch("utils.wikidata.time.sleep"):
            mock_sparql = MagicMock()
            mock_sparql.query.side_effect = urllib.error.HTTPError(
                url="", code=429, msg="Too Many Requests", hdrs={}, fp=None
            )
            mock_client_fn.return_value = mock_sparql

            with pytest.raises(urllib.error.HTTPError):
                fetch_page("Q901", offset=0, max_retries=2)
