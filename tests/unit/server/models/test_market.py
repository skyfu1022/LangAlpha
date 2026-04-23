"""Tests for validate_market utility."""

import pytest
from fastapi import HTTPException

from src.server.models.market import validate_market


class TestValidateMarketDefaults:
    """Default and valid-value cases."""

    def test_none_returns_us(self):
        assert validate_market(None) == "us"

    def test_us_returns_us(self):
        assert validate_market("us") == "us"

    def test_cn_returns_cn(self):
        assert validate_market("cn") == "cn"


class TestValidateMarketCaseNormalization:
    """Upper-case inputs should be normalized to lower-case."""

    def test_uppercase_us(self):
        assert validate_market("US") == "us"

    def test_uppercase_cn(self):
        assert validate_market("CN") == "cn"


class TestValidateMarketWhitespaceTrimming:
    """Leading/trailing whitespace should be stripped."""

    def test_padded_us(self):
        assert validate_market(" us ") == "us"

    def test_padded_cn(self):
        assert validate_market(" cn ") == "cn"


class TestValidateMarketInvalidValues:
    """Invalid market strings must raise HTTPException with status 400."""

    @pytest.mark.parametrize("value", ["xyz", "hk"])
    def test_invalid_market_raises_400(self, value: str):
        with pytest.raises(HTTPException) as exc_info:
            validate_market(value)
        assert exc_info.value.status_code == 400

    def test_empty_string_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_market("")
        assert exc_info.value.status_code == 400

    def test_whitespace_only_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_market("  ")
        assert exc_info.value.status_code == 400


class TestValidateMarketErrorMessage:
    """Error detail must include the original (invalid) value."""

    def test_error_message_contains_invalid_value(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_market("hk")
        assert "hk" in exc_info.value.detail
