"""점수 계산 단위 테스트. (담당: 이태우)"""
from app.services.scoring_service import ScoringService


class TestScoringService:
    def test_night_activity_scores(self):
        """야간 활동 입력 시 night_score 가 높아야 함."""
        service = ScoringService()
        scores = service.calculate_lifestyle_scores({
            "main_activity_time": "야간 활동",
            "daytime_home_stay": "거의 없음",
            "sleep_time": "새벽",
            "outdoor_activity": "보통",
            "hot_time_home_stay": "가끔",
        })
        assert scores["night_score"] == 5  # 3 + 2
        assert scores["outing_score"] == 4  # 3 + 1

    def test_stay_home_scores(self):
        """종일 재택 입력 시 stay_home_score 가 높아야 함."""
        service = ScoringService()
        scores = service.calculate_lifestyle_scores({
            "main_activity_time": "아침형",
            "daytime_home_stay": "종일 재택",
            "sleep_time": "밤",
            "outdoor_activity": "적음",
            "hot_time_home_stay": "거의 항상",
        })
        assert scores["stay_home_score"] == 4  # 3 + 1
        assert scores["cooling_need_score"] == 3
