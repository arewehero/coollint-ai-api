"""Calculation Engine for energy, saving, and CO₂ computations.

Provides pure functions for:
- Energy consumption (kWh)
- Saving amount (KRW)
- CO₂ reduction (kg)
- Temperature coefficient mapping
- AC power estimation by room size
- Input validation

All formulas follow the design specification:
- kWh = power_W × temp_coeff × hours ÷ 1000 (rounded to 3 decimals)
- KRW = kWh × unit_price (rounded to integer)
- CO₂_kg = kWh × 0.4781 (rounded to 4 decimals)
"""

from __future__ import annotations

from typing import Optional

from app.core.errors import ApiException, ErrorCode

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CO2_EMISSION_FACTOR: float = 0.4781  # kg CO₂ per kWh
DEFAULT_UNIT_PRICE: int = 150  # 원/kWh
DEFAULT_AC_POWER_WATT: int = 1200  # W

# Temperature coefficient mapping (design spec)
_TEMP_COEFFICIENTS: dict[str, float] = {
    "high": 0.92,   # 26°C 이상
    "normal": 1.00,  # 25°C
    "low": 1.08,    # 24°C
    "very_low": 1.17,  # 23°C 이하
}

# Room size to AC power watt mapping
_ROOM_SIZE_POWER_MAP: dict[str, int] = {
    "~6평": 750,
    "7~10평": 1200,
    "11~14평": 1800,
    "15평~": 2200,
}


# ---------------------------------------------------------------------------
# Input Validation
# ---------------------------------------------------------------------------


def validate_calculation_inputs(
    *,
    power_watt: Optional[int] = None,
    usage_hours: Optional[float] = None,
    unit_price: Optional[int] = None,
    temp_setting: Optional[float] = None,
) -> None:
    """Validate calculation input ranges.

    Raises ApiException (VALIDATION_ERROR, 422) if any provided value
    is outside its valid range.

    Valid ranges:
    - power_watt: 1 ~ 5000 (W)
    - usage_hours: 0 ~ 24 (h)
    - unit_price: 1 ~ 1000 (원/kWh)
    - temp_setting: 18 ~ 30 (°C)

    Only validates parameters that are not None.
    """
    errors: dict[str, str] = {}

    if power_watt is not None and not (1 <= power_watt <= 5000):
        errors["power_watt"] = "소비전력은 1~5000W 범위여야 합니다."

    if usage_hours is not None and not (0 <= usage_hours <= 24):
        errors["usage_hours"] = "사용시간은 0~24h 범위여야 합니다."

    if unit_price is not None and not (1 <= unit_price <= 1000):
        errors["unit_price"] = "전기요금 단가는 1~1000원/kWh 범위여야 합니다."

    if temp_setting is not None and not (18 <= temp_setting <= 30):
        errors["temp_setting"] = "설정 온도는 18~30°C 범위여야 합니다."

    if errors:
        raise ApiException.from_error_code(
            ErrorCode.VALIDATION_ERROR,
            message="계산 입력값이 유효 범위를 벗어났습니다.",
            details=errors,
        )


# ---------------------------------------------------------------------------
# Temperature Coefficient
# ---------------------------------------------------------------------------


def temperature_coefficient(temp_setting: float) -> float:
    """Return temperature coefficient based on the AC setting temperature.

    Mapping:
    - 26°C 이상: 0.92 (에너지 절약)
    - 25°C (25 <= T < 26): 1.00 (기준)
    - 24°C (24 <= T < 25): 1.08
    - 23°C 이하 (T < 24): 1.17 (에너지 증가)
    """
    if temp_setting >= 26:
        return 0.92
    elif temp_setting >= 25:
        return 1.00
    elif temp_setting >= 24:
        return 1.08
    else:
        return 1.17


# ---------------------------------------------------------------------------
# Power Estimation
# ---------------------------------------------------------------------------


def estimate_ac_power_watt(
    ac_power_watt: Optional[int] = None,
    room_size: Optional[str] = None,
) -> int:
    """Estimate AC power consumption in watts.

    Priority:
    1. If ac_power_watt is provided (> 0), use it directly.
    2. If room_size is provided and in the lookup table, use the mapped value.
    3. Otherwise, return the default 1200W.
    """
    if ac_power_watt is not None and ac_power_watt > 0:
        return ac_power_watt

    if room_size is not None and room_size in _ROOM_SIZE_POWER_MAP:
        return _ROOM_SIZE_POWER_MAP[room_size]

    return DEFAULT_AC_POWER_WATT


# ---------------------------------------------------------------------------
# Core Calculation Functions
# ---------------------------------------------------------------------------


def calculate_energy_kwh(power_watt: int, temp_coeff: float, usage_hours: float) -> float:
    """Calculate energy consumption in kWh.

    Formula: kWh = power_W × temp_coeff × hours ÷ 1000
    Result is rounded to 3 decimal places.
    """
    return round((power_watt * temp_coeff * usage_hours) / 1000, 3)


def calculate_saving_krw(energy_saving_kwh: float, unit_price: int = DEFAULT_UNIT_PRICE) -> int:
    """Calculate monetary saving in KRW.

    Formula: KRW = energy_saving_kwh × unit_price
    Result is rounded to the nearest integer.
    Default unit_price: 150 KRW/kWh.
    """
    return round(energy_saving_kwh * unit_price)


def calculate_co2_reduction(energy_saving_kwh: float) -> float:
    """Calculate CO₂ reduction in kg.

    Formula: CO₂_kg = energy_saving_kwh × 0.4781
    Result is rounded to 4 decimal places.
    """
    return round(energy_saving_kwh * CO2_EMISSION_FACTOR, 4)
