import pytest
from decimal import Decimal
from unittest import mock

from ...services.calculation.volatility import (
    calculate_volatility_adjustment,
    apply_volatility_adjustment,
    get_volatility_data,
    validate_volatility_index,
    get_volatility_tier,
    format_volatility_adjustment
)

from ...core.constants import DEFAULT_VOLATILITY_FACTOR
from ...core.exceptions import CalculationException, ExternalAPIException

from ...services.external.market_api import (
    get_stock_volatility,
    get_market_volatility_index
)

from ..fixtures.volatility import (
    low_volatility_data,
    high_volatility_data,
    medium_volatility_data,
    extreme_volatility_data
)

from ..conftest import mock_market_volatility_api


def test_validate_volatility_index_with_valid_value():
    # Test with Decimal
    result1 = validate_volatility_index(Decimal('20.5'))
    assert isinstance(result1, Decimal)
    assert result1 == Decimal('20.5')
    
    # Test with float
    result2 = validate_volatility_index(15.3)
    assert isinstance(result2, Decimal)
    assert result2 == Decimal('15.3')
    
    # Test with string
    result3 = validate_volatility_index('25.7')
    assert isinstance(result3, Decimal)
    assert result3 == Decimal('25.7')


def test_validate_volatility_index_with_none():
    result = validate_volatility_index(None)
    assert result == DEFAULT_VOLATILITY_FACTOR


def test_validate_volatility_index_with_negative_value():
    with pytest.raises(CalculationException) as exc_info:
        validate_volatility_index(-5.0)
    assert "cannot be negative" in str(exc_info.value)


def test_calculate_volatility_adjustment_low_volatility(low_volatility_data):
    vol_index = low_volatility_data['vol_index']
    adjustment = calculate_volatility_adjustment(vol_index)
    
    # Should be vol_index * DEFAULT_VOLATILITY_MULTIPLIER
    expected = vol_index * Decimal('0.01')
    assert adjustment == expected
    
    # Should be relatively small for low volatility
    assert adjustment < Decimal('0.2')


def test_calculate_volatility_adjustment_high_volatility(high_volatility_data):
    vol_index = high_volatility_data['vol_index']
    adjustment = calculate_volatility_adjustment(vol_index)
    
    # For high volatility, there should be additional adjustment
    expected_base = vol_index * Decimal('0.01')
    assert adjustment > expected_base
    
    # Should be significant for high volatility
    assert adjustment > Decimal('0.3')


def test_calculate_volatility_adjustment_extreme_volatility(extreme_volatility_data):
    vol_index = extreme_volatility_data['vol_index']
    adjustment = calculate_volatility_adjustment(vol_index)
    
    # For extreme volatility, there should be substantial additional adjustment
    expected_base = vol_index * Decimal('0.01')
    assert adjustment > expected_base
    
    # Should be very significant for extreme volatility
    assert adjustment > Decimal('0.5')


def test_calculate_volatility_adjustment_custom_multiplier(medium_volatility_data):
    vol_index = medium_volatility_data['vol_index']
    custom_multiplier = Decimal('0.02')  # Double the default multiplier
    
    adjustment = calculate_volatility_adjustment(vol_index, custom_multiplier)
    
    # Should be vol_index * custom_multiplier (plus any additional for high volatility)
    expected_base = vol_index * custom_multiplier
    
    # With custom multiplier, adjustment should be approximately 2x the default
    default_adjustment = calculate_volatility_adjustment(vol_index)
    assert adjustment > default_adjustment


def test_apply_volatility_adjustment(medium_volatility_data):
    base_rate = Decimal('0.05')  # 5% base rate
    vol_index = medium_volatility_data['vol_index']
    
    adjusted_rate = apply_volatility_adjustment(base_rate, vol_index)
    
    # Manually calculate expected rate
    volatility_adjustment = calculate_volatility_adjustment(vol_index)
    expected_rate = base_rate * (Decimal('1') + volatility_adjustment)
    
    assert adjusted_rate == expected_rate
    assert adjusted_rate > base_rate  # Rate should increase with volatility


def test_get_volatility_tier():
    # Test different volatility tiers
    assert get_volatility_tier(Decimal('15')) == 'LOW'
    assert get_volatility_tier(Decimal('25')) == 'NORMAL'
    assert get_volatility_tier(Decimal('35')) == 'HIGH'
    assert get_volatility_tier(Decimal('45')) == 'EXTREME'
    
    # Test boundary values
    assert get_volatility_tier(Decimal('19.9999')) == 'LOW'
    assert get_volatility_tier(Decimal('20')) == 'NORMAL'
    assert get_volatility_tier(Decimal('29.9999')) == 'NORMAL'
    assert get_volatility_tier(Decimal('30')) == 'HIGH'
    assert get_volatility_tier(Decimal('39.9999')) == 'HIGH'
    assert get_volatility_tier(Decimal('40')) == 'EXTREME'


def test_format_volatility_adjustment():
    original_rate = Decimal('0.05')
    adjusted_rate = Decimal('0.065')
    volatility_index = Decimal('25')
    
    result = format_volatility_adjustment(original_rate, adjusted_rate, volatility_index)
    
    # Check that all expected fields are present
    assert 'original_rate' in result
    assert 'adjusted_rate' in result
    assert 'volatility_index' in result
    assert 'volatility_tier' in result
    assert 'adjustment_amount' in result
    assert 'adjustment_percentage' in result
    
    # Check correct values
    assert result['original_rate'] == float(original_rate)
    assert result['adjusted_rate'] == float(adjusted_rate)
    assert result['volatility_index'] == float(volatility_index)
    assert result['volatility_tier'] == 'NORMAL'
    assert result['adjustment_amount'] == float(adjusted_rate - original_rate)
    assert result['adjustment_percentage'] == float((adjusted_rate / original_rate - Decimal('1')) * Decimal('100'))


def test_get_volatility_data_stock_specific(mock_market_volatility_api):
    ticker = 'AAPL'
    result = get_volatility_data(ticker)
    
    assert 'volatility' in result
    assert result['ticker'] == ticker
    assert 'timestamp' in result


def test_get_volatility_data_market(mock_market_volatility_api):
    result = get_volatility_data()  # No ticker specified should get market data
    
    assert 'value' in result
    assert 'timestamp' in result


def test_get_volatility_data_fallback():
    # Mock the external API calls to simulate failure
    with mock.patch('src.backend.services.external.market_api.get_stock_volatility',
                   side_effect=ExternalAPIException('market_volatility', 'API unavailable')):
        with mock.patch('src.backend.services.external.market_api.get_market_volatility_index',
                      side_effect=ExternalAPIException('market_volatility', 'API unavailable')):
            
            # Should use fallback values
            result = get_volatility_data('AAPL')
            
            # Verify we got default values
            assert result is not None
            assert isinstance(result, dict)