"""전력량·요금·CO₂ 계산 서비스. (담당: 이태우)"""

from app.core.config import settings


ROOM_SIZE_TO_WATT = {
    "~6평": 750,
    "7~10평": 1200,
    "11~14평": 1800,
    "15평~": 2200,
}

TEMPERATURE_COEFFICIENTS = {
    26: 0.92,
    25: 1.00,
    24: 1.08,
    23: 1.17,
}


def estimate_ac_power_watt(ac_power_watt: int | None, room_size: str | None) -> int:
    """소비전력 추정. 직접 입력값 우선, 없으면 방 평수 기반."""
    if ac_power_watt:
        return ac_power_watt
    return ROOM_SIZE_TO_WATT.get(room_size, 1200)


def temperature_coefficient(temp_c: float) -> float:
    """온도 보정 계수 반환."""
    if temp_c >= 26:
        return 0.92
    if temp_c >= 25:
        return 1.00
    if temp_c >= 24:
        return 1.08
    return 1.17


def calculate_energy_kwh(power_watt: int, temp_coeff: float, usage_hours: float) -> float:
    """전력량(kWh) = 소비전력(W) × 온도 보정 계수 × 사용시간(h) ÷ 1000"""
    return (power_watt * temp_coeff * usage_hours) / 1000


def calculate_saving_krw(energy_saving_kwh: float, unit_price: float | None = None) -> int:
    """예상 절약액(원) = 절감 전력량 × 전기요금 단가."""
    price = unit_price or settings.DEFAULT_ELECTRICITY_UNIT_PRICE
    return round(energy_saving_kwh * price)


def calculate_co2_reduction(energy_saving_kwh: float) -> float:
    """CO₂ 감축량(kg) = 절감 전력량 × 배출계수."""
    return round(energy_saving_kwh * settings.CO2_FACTOR_KG_PER_KWH, 4)
