"""행동 후보 생성 서비스. (담당: 임혜성)"""
from typing import Any


class RecommendationCandidateService:
    """백엔드가 AI 호출 전에 행동 후보를 생성한다."""

    def generate_candidates(
        self,
        lifestyle_type: str,
        home_env: dict,
        weather_blocks: list[dict],
        profile: dict,
        scores: dict,
    ) -> list[dict[str, Any]]:
        """조건 기반으로 행동 후보 목록을 생성한다."""
        candidates = []

        has_ac = profile.get("ac_type", "없음") != "없음"
        has_fan = profile.get("has_fan", False)
        morning_temp = self._get_block_temp(weather_blocks, "06:00~09:00")
        noon_temp = self._get_block_temp(weather_blocks, "12:00~15:00")
        afternoon_temp = self._get_block_temp(weather_blocks, "15:00~18:00")
        morning_rain = self._get_block_rain(weather_blocks, "06:00~09:00")

        # morning_ventilation
        if morning_temp is not None and morning_temp < 28 and not morning_rain and home_env.get("ventilation_level") != "잘 안됨":
            candidates.append(self._make_candidate("morning_ventilation", "06:00~09:00", "쉬움"))

        # pre_shading
        if noon_temp is not None and noon_temp >= 28:
            candidates.append(self._make_candidate("pre_shading", "09:00~12:00", "쉬움"))

        # shading_before_outing
        if scores.get("outing_score", 0) >= 3 and (noon_temp or 30) >= 28:
            candidates.append(self._make_candidate("shading_before_outing", "외출 전", "쉬움"))

        # ac_temp_up
        current_temp = profile.get("current_temperature_setting")
        if has_ac and current_temp is not None and current_temp < 26:
            candidates.append(self._make_candidate("ac_temp_up", "냉방 시", "쉬움"))

        # fan_with_ac
        if has_ac and has_fan:
            candidates.append(self._make_candidate("fan_with_ac", "냉방 시", "쉬움"))

        # timer_sleep
        if has_ac and scores.get("night_score", 0) >= 2:
            candidates.append(self._make_candidate("timer_sleep", "23:00~02:00", "쉬움"))

        # close_window_check
        if home_env.get("window_sealing") == "틈새 있음" or home_env.get("insulation_level") == "약함":
            candidates.append(self._make_candidate("close_window_check", "냉방 전", "쉬움"))

        # room_zone_cooling
        if home_env.get("housing_type") != "원룸" and scores.get("cooling_loss_score", 0) >= 3:
            candidates.append(self._make_candidate("room_zone_cooling", "냉방 시", "보통"))

        # rainy_air_circulation
        noon_rain = self._get_block_rain(weather_blocks, "12:00~15:00")
        noon_humidity = self._get_block_humidity(weather_blocks, "12:00~15:00")
        if noon_rain or (noon_humidity and noon_humidity >= 70):
            candidates.append(self._make_candidate("rainy_air_circulation", "12:00~15:00", "쉬움"))

        # safety_cooling
        if (noon_temp and noon_temp >= 35) or (afternoon_temp and afternoon_temp >= 35):
            candidates.append(self._make_candidate("safety_cooling", "12:00~18:00", "쉬움"))

        return candidates

    def _make_candidate(self, action_type: str, time_range: str, difficulty: str) -> dict:
        return {
            "candidate_id": f"cand_{action_type}",
            "time_range": time_range,
            "action_type": action_type,
            "difficulty": difficulty,
            "estimated_saving_krw": 0,
            "estimated_energy_saving_kwh": 0.0,
            "estimated_co2_reduction_kg": 0.0,
            "evidence": [],
            "backend_hint": "",
        }

    def _get_block_temp(self, blocks: list[dict], time_range: str) -> float | None:
        for b in blocks:
            if b.get("time_range") == time_range:
                return b.get("temperature")
        return None

    def _get_block_rain(self, blocks: list[dict], time_range: str) -> bool:
        for b in blocks:
            if b.get("time_range") == time_range:
                return b.get("rain", False)
        return False

    def _get_block_humidity(self, blocks: list[dict], time_range: str) -> int | None:
        for b in blocks:
            if b.get("time_range") == time_range:
                return b.get("humidity")
        return None
