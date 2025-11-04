"""Unit tests for the payload normalization shim used by the REST API."""
from types import SimpleNamespace

import pytest

from tiger_rest_api_full import _normalize_payload


class DummyDataFrame:
    """Simulates a pandas DataFrame providing a to_dict(orient='records') signature."""

    def __init__(self, rows):
        self._rows = rows

    def to_dict(self, orient=None):
        if orient != "records":
            raise ValueError("Expected orient='records'")
        return self._rows


class DictLikeToDict:
    """Simulates objects that only support a zero-argument to_dict()."""

    def __init__(self, payload):
        self._payload = payload

    def to_dict(self):
        return self._payload


class IterableWrapper:
    """Iterable object that is not a builtin list/tuple."""

    def __init__(self, data):
        self._data = data

    def __iter__(self):
        yield from self._data


def test_normalize_none_returns_empty_list():
    assert _normalize_payload(None) == []


def test_normalize_list_of_dicts_wraps_into_namespace():
    payload = [{"symbol": "AAPL", "price": 189.12}, {"symbol": "TSLA", "price": 196.3}]

    result = _normalize_payload(payload)

    assert len(result) == 2
    assert isinstance(result[0], SimpleNamespace)
    assert result[0].symbol == "AAPL"
    assert result[1].price == pytest.approx(196.3)


def test_normalize_dict_returns_single_namespace():
    payload = {"symbol": "AAPL", "volume": 12345}

    result = _normalize_payload(payload)

    assert len(result) == 1
    assert isinstance(result[0], SimpleNamespace)
    assert result[0].volume == 12345


def test_normalize_dataframe_like_object():
    payload = DummyDataFrame(
        [
            {"symbol": "AAPL", "price": 189.12},
            {"symbol": "MSFT", "price": 411.29},
        ]
    )

    result = _normalize_payload(payload)

    assert len(result) == 2
    assert result[1].symbol == "MSFT"
    assert result[1].price == pytest.approx(411.29)


def test_normalize_to_dict_without_orient():
    payload = DictLikeToDict({"symbol": "AMZN", "price": 131.52})

    result = _normalize_payload(payload)

    assert len(result) == 1
    assert isinstance(result[0], SimpleNamespace)
    assert result[0].symbol == "AMZN"


def test_normalize_iterable_wrapper():
    payload = IterableWrapper([{"symbol": "BABA"}, {"symbol": "BIDU"}])

    result = _normalize_payload(payload)

    extracted = [item.symbol for item in result]
    assert extracted == ["BABA", "BIDU"]


def test_normalize_scalar_value_preserves_object():
    payload = 42

    result = _normalize_payload(payload)

    assert result == [42]


def test_normalize_leaves_strings_intact():
    payload = "raw-token-value"

    result = _normalize_payload(payload)

    assert result == ["raw-token-value"]
