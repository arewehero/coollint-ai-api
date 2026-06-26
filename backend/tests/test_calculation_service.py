"""전력량/요금/CO₂ 계산 단위 테스트. (담당: 이태우)"""
from app.services.calculation_service import (
    estimate_ac_power_watt,
    temperature_coefficient,
    calculate_energy_kwh,
    calculate_saving_krw,
    calculate_co2_reduction,
)


class TestCalculationService:
    def test_estimate_ac_power_direct(self):
        assert estimate_ac_power_watt(1500, "7~10평") == 1500

    def test_estimate_ac_power_from_room_size(self):
        assert estimate_ac_power_watt(None, "~6평") == 750
        assert estimate_ac_power_watt(None, "15평~") == 2200

    def test_estimate_ac_power_default(self):
        assert estimate_ac_power_watt(None, None) == 1200

    def test_temperature_coefficient(self):
        assert temperature_coefficient(26) == 0.92
        assert temperature_coefficient(24) == 1.08
        assert temperature_coefficient(22) == 1.17

    def test_energy_calculation(self):
        # 1200W, 1.08 계수, 6시간
        energy = calculate_energy_kwh(1200, 1.08, 6)
        assert abs(energy - 7.776) < 0.001

    def test_saving_krw(self):
        saving = calculate_saving_krw(1.0, 150)
        assert saving == 150

    def test_co2_reduction(self):
        co2 = calculate_co2_reduction(1.0)
        assert abs(co2 - 0.4781) < 0.001
