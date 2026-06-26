"""Unit tests for CalculationService.

Validates Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7.
"""

import pytest

from app.core.errors import ApiException
from app.services.calculation_service import (
    DEFAULT_UNIT_PRICE,
    calculate_co2_reduction,
    calculate_energy_kwh,
    calculate_saving_krw,
    estimate_ac_power_watt,
    temperature_coefficient,
    validate_calculation_inputs,
)


# ---------------------------------------------------------------------------
# calculate_energy_kwh
# ---------------------------------------------------------------------------


class TestCalculateEnergyKwh:
    """Requirement 9.1: kWh = power_W × temp_coeff × hours ÷ 1000, round 3."""

    def test_basic_calculation(self):
        # 1200W * 1.0 * 8h / 1000 = 9.6
        assert calculate_energy_kwh(1200, 1.0, 8.0) == 9.6

    def test_rounding_to_3_decimals(self):
        # 750W * 1.08 * 3.5h / 1000 = 2.835
        result = calculate_energy_kwh(750, 1.08, 3.5)
        assert result == 2.835

    def test_zero_hours(self):
        assert calculate_energy_kwh(1200, 1.0, 0.0) == 0.0

    def test_high_power_full_day(self):
        # 5000W * 0.92 * 24h / 1000 = 110.4
        assert calculate_energy_kwh(5000, 0.92, 24.0) == 110.4

    def test_temp_coeff_117(self):
        # 1200W * 1.17 * 10h / 1000 = 14.04
        assert calculate_energy_kwh(1200, 1.17, 10.0) == 14.04


# ---------------------------------------------------------------------------
# calculate_saving_krw
# ---------------------------------------------------------------------------


class TestCalculateSavingKrw:
    """Requirement 9.2: KRW = kWh × unit_price, round to int."""

    def test_basic_saving(self):
        # 9.6 * 150 = 1440
        assert calculate_saving_krw(9.6, 150) == 1440

    def test_default_unit_price(self):
        # 9.6 * 150 = 1440 (default)
        assert calculate_saving_krw(9.6) == 1440

    def test_rounding_to_integer(self):
        # 2.835 * 150 = 425.25 → 425
        assert calculate_saving_krw(2.835, 150) == 425

    def test_zero_energy(self):
        assert calculate_saving_krw(0.0, 150) == 0

    def test_custom_unit_price(self):
        # 5.0 * 200 = 1000
        assert calculate_saving_krw(5.0, 200) == 1000


# ---------------------------------------------------------------------------
# calculate_co2_reduction
# ---------------------------------------------------------------------------


class TestCalculateCo2Reduction:
    """Requirement 9.3: CO₂_kg = kWh × 0.4781, round 4."""

    def test_basic_co2(self):
        # 9.6 * 0.4781 = 4.58976 → 4.5898
        assert calculate_co2_reduction(9.6) == 4.5898

    def test_zero_energy(self):
        assert calculate_co2_reduction(0.0) == 0.0

    def test_small_energy(self):
        # 0.5 * 0.4781 = 0.23905 → 0.2391
        assert calculate_co2_reduction(0.5) == 0.2391


# ---------------------------------------------------------------------------
# temperature_coefficient
# ---------------------------------------------------------------------------


class TestTemperatureCoefficient:
    """Requirement 9.6: temp coeff mapping."""

    def test_26_or_above(self):
        assert temperature_coefficient(26.0) == 0.92
        assert temperature_coefficient(28.0) == 0.92
        assert temperature_coefficient(30.0) == 0.92

    def test_25_range(self):
        assert temperature_coefficient(25.0) == 1.00
        assert temperature_coefficient(25.5) == 1.00

    def test_24_range(self):
        assert temperature_coefficient(24.0) == 1.08
        assert temperature_coefficient(24.9) == 1.08

    def test_below_24(self):
        assert temperature_coefficient(23.0) == 1.17
        assert temperature_coefficient(18.0) == 1.17
        assert temperature_coefficient(23.9) == 1.17


# ---------------------------------------------------------------------------
# estimate_ac_power_watt
# ---------------------------------------------------------------------------


class TestEstimateAcPowerWatt:
    """Requirement 9.5: power estimation lookup."""

    def test_user_provided_value(self):
        assert estimate_ac_power_watt(ac_power_watt=2000, room_size="~6평") == 2000

    def test_room_size_6pyeong(self):
        assert estimate_ac_power_watt(None, "~6평") == 750

    def test_room_size_7_10pyeong(self):
        assert estimate_ac_power_watt(None, "7~10평") == 1200

    def test_room_size_11_14pyeong(self):
        assert estimate_ac_power_watt(None, "11~14평") == 1800

    def test_room_size_15pyeong_plus(self):
        assert estimate_ac_power_watt(None, "15평~") == 2200

    def test_default_no_info(self):
        assert estimate_ac_power_watt(None, None) == 1200

    def test_unknown_room_size(self):
        assert estimate_ac_power_watt(None, "알 수 없음") == 1200

    def test_zero_ac_power_uses_room_size(self):
        # ac_power_watt=0 means not provided (not > 0)
        assert estimate_ac_power_watt(0, "~6평") == 750


# ---------------------------------------------------------------------------
# validate_calculation_inputs
# ---------------------------------------------------------------------------


class TestValidateCalculationInputs:
    """Requirement 9.7: input validation ranges."""

    def test_valid_inputs_pass(self):
        # Should not raise
        validate_calculation_inputs(
            power_watt=1200,
            usage_hours=8.0,
            unit_price=150,
            temp_setting=26.0,
        )

    def test_power_watt_below_range(self):
        with pytest.raises(ApiException) as exc_info:
            validate_calculation_inputs(power_watt=0)
        assert exc_info.value.code == "VALIDATION_ERROR"
        assert "power_watt" in exc_info.value.details

    def test_power_watt_above_range(self):
        with pytest.raises(ApiException) as exc_info:
            validate_calculation_inputs(power_watt=5001)
        assert exc_info.value.code == "VALIDATION_ERROR"

    def test_usage_hours_below_range(self):
        with pytest.raises(ApiException) as exc_info:
            validate_calculation_inputs(usage_hours=-1.0)
        assert exc_info.value.code == "VALIDATION_ERROR"

    def test_usage_hours_above_range(self):
        with pytest.raises(ApiException) as exc_info:
            validate_calculation_inputs(usage_hours=25.0)
        assert exc_info.value.code == "VALIDATION_ERROR"

    def test_unit_price_below_range(self):
        with pytest.raises(ApiException) as exc_info:
            validate_calculation_inputs(unit_price=0)
        assert exc_info.value.code == "VALIDATION_ERROR"

    def test_unit_price_above_range(self):
        with pytest.raises(ApiException) as exc_info:
            validate_calculation_inputs(unit_price=1001)
        assert exc_info.value.code == "VALIDATION_ERROR"

    def test_temp_setting_below_range(self):
        with pytest.raises(ApiException) as exc_info:
            validate_calculation_inputs(temp_setting=17.0)
        assert exc_info.value.code == "VALIDATION_ERROR"

    def test_temp_setting_above_range(self):
        with pytest.raises(ApiException) as exc_info:
            validate_calculation_inputs(temp_setting=31.0)
        assert exc_info.value.code == "VALIDATION_ERROR"

    def test_boundary_values_valid(self):
        # All boundary values should pass
        validate_calculation_inputs(power_watt=1)
        validate_calculation_inputs(power_watt=5000)
        validate_calculation_inputs(usage_hours=0.0)
        validate_calculation_inputs(usage_hours=24.0)
        validate_calculation_inputs(unit_price=1)
        validate_calculation_inputs(unit_price=1000)
        validate_calculation_inputs(temp_setting=18.0)
        validate_calculation_inputs(temp_setting=30.0)

    def test_multiple_invalid_fields(self):
        with pytest.raises(ApiException) as exc_info:
            validate_calculation_inputs(
                power_watt=0,
                usage_hours=25.0,
                unit_price=0,
                temp_setting=31.0,
            )
        assert exc_info.value.code == "VALIDATION_ERROR"
        assert len(exc_info.value.details) == 4

    def test_none_values_skip_validation(self):
        # Should not raise when all None
        validate_calculation_inputs()
