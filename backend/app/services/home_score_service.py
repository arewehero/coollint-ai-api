"""집 환경 점수 계산 서비스. (담당: 이태우)"""


class HomeScoreService:
    """집 환경 입력을 기반으로 열 유입/냉방 손실/자연 환기 가능 점수를 계산한다."""

    def calculate_home_scores(self, home_env: dict, weather_morning_temp: float | None = None, rain: bool = False) -> dict:
        scores = {
            "heat_gain_score": 0,
            "cooling_loss_score": 0,
            "ventilation_score": 0,
        }

        # 열 유입 점수
        direction = home_env.get("direction", "")
        if direction in ("서향", "남서향"):
            scores["heat_gain_score"] += 3
        elif direction == "남향":
            scores["heat_gain_score"] += 2

        floor_level = home_env.get("floor_level", "")
        if floor_level == "최상층":
            scores["heat_gain_score"] += 3
        elif floor_level == "고층":
            scores["heat_gain_score"] += 1

        if home_env.get("window_size") == "큼":
            scores["heat_gain_score"] += 2

        if home_env.get("curtain_type", "없음") == "없음":
            scores["heat_gain_score"] += 2

        # 냉방 손실 점수
        if home_env.get("insulation_level") == "약함":
            scores["cooling_loss_score"] += 3
        if home_env.get("building_age") == "노후":
            scores["cooling_loss_score"] += 2
        if home_env.get("window_sealing") == "틈새 있음":
            scores["cooling_loss_score"] += 3
        if home_env.get("ventilation_level") == "잘 안됨":
            scores["cooling_loss_score"] += 2  # air_circulation_issue

        # 자연 환기 가능 점수
        if home_env.get("ventilation_level") == "잘됨":
            scores["ventilation_score"] += 3
        if home_env.get("window_size") == "큼":
            scores["ventilation_score"] += 1
        if weather_morning_temp is not None and weather_morning_temp < 28:
            scores["ventilation_score"] += 2
        if not rain:
            scores["ventilation_score"] += 1

        return scores
