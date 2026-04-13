"""Unit tests for the payload normalization shim used by the REST API."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import tiger_rest_api_full
from tiger_rest_api_full import (
    app,
    _normalize_payload,
    _normalize_position_quantity,
    _structure_option_chain,
    _to_plain_dict,
)


class DummyDataFrame:
    """Simulates a pandas DataFrame providing a to_dict(orient='records') signature."""

    def __init__(self, rows):
        self._rows = rows

    def to_dict(self, orient=None):
        if orient != "records":
            raise ValueError("Expected orient='records'")
        return self._rows


class AmbiguousRecords:
    """Iterable that raises on truthiness, mimicking pandas.DataFrame behaviour."""

    def __init__(self, rows):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)

    def __bool__(self):
        raise ValueError("The truth value of a DataFrame is ambiguous")


class AmbiguousDataFrame(DummyDataFrame):
    """DataFrame variant that surfaces ambiguous truthiness via to_dict return."""

    def to_dict(self, orient=None):
        base = super().to_dict(orient=orient)
        return AmbiguousRecords(base)


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


def test_normalize_dataframe_with_ambiguous_truthiness():
    payload = AmbiguousDataFrame(
        [
            {"symbol": "NVDA", "price": 118.45},
            {"symbol": "AMD", "price": 31.84},
        ]
    )

    result = _normalize_payload(payload)

    assert [item.symbol for item in result] == ["NVDA", "AMD"]


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


def test_to_plain_dict_handles_simple_namespace():
    item = SimpleNamespace(strike=150, put_call="CALL")

    result = _to_plain_dict(item)

    assert result == {"strike": 150, "put_call": "CALL"}


class ContractObject:
    def __init__(self, strike, side):
        self.strike = strike
        self.put_call = side
        self.last_price = 1.25


def test_to_plain_dict_handles_custom_object():
    item = ContractObject(125, "PUT")

    result = _to_plain_dict(item)

    assert result["strike"] == 125
    assert result["put_call"] == "PUT"
    assert result["last_price"] == 1.25


def test_structure_option_chain_splits_calls_puts_other():
    payload = [
        {"put_call": "CALL", "strike": 100},
        {"put_call": "PUT", "strike": 110},
        {"strike": 120},
    ]

    structured = _structure_option_chain(payload)

    assert structured["total"] == 3
    assert [c["strike"] for c in structured["calls"]] == [100]
    assert [p["strike"] for p in structured["puts"]] == [110]
    assert [o["strike"] for o in structured["other"]] == [120]


class DummyTradeClient:
    def __init__(self, positions):
        self._positions = positions

    def get_positions(self):
        return self._positions


def test_normalize_position_quantity_prefers_decoded_position_qty():
    position = SimpleNamespace(
        quantity=100067952,
        position_qty=1000.67952,
        position_scale=5,
    )

    assert _normalize_position_quantity(position) == pytest.approx(1000.67952)


def test_normalize_position_quantity_falls_back_to_scaled_raw_quantity():
    position = SimpleNamespace(quantity=12345, position_scale=2)

    assert _normalize_position_quantity(position) == pytest.approx(123.45)


def test_positions_endpoint_returns_normalized_fractional_quantity(monkeypatch):
    positions = [
        SimpleNamespace(
            contract=SimpleNamespace(symbol="DUOL"),
            quantity=100067952,
            position_qty=1000.67952,
            position_scale=5,
            average_cost=256.0827,
            market_price=89.82,
            market_value=89881.0345,
            unrealized_pnl=-166375.65,
        ),
        SimpleNamespace(
            contract=SimpleNamespace(symbol="09961"),
            quantity=250,
            position_qty=250.0,
            position_scale=0,
            average_cost=471.9319,
            market_price=397.2,
            market_value=99300.0,
            unrealized_pnl=-18682.97,
        ),
    ]

    monkeypatch.setattr(
        tiger_rest_api_full,
        "get_tiger_client",
        lambda account: {"trade": DummyTradeClient(positions)},
    )

    client = TestClient(app)
    response = client.post(
        "/api/trade/positions",
        headers={"Authorization": "Bearer client_key_001"},
        json={"account": "67686635"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    returned_positions = payload["data"]["positions"]
    duol = next(
        position for position in returned_positions if position["symbol"] == "DUOL"
    )
    hk = next(
        position for position in returned_positions if position["symbol"] == "09961"
    )

    assert duol["quantity"] == pytest.approx(1000.67952)
    assert duol["quantity_raw"] == 100067952
    assert duol["quantity_scale"] == 5
    assert hk["quantity"] == 250
    assert isinstance(hk["quantity"], int)
