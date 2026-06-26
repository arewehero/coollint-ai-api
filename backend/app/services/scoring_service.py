"""생활패턴 점수 계산 서비스. (담당: 이태우)"""


class ScoringService:
    """사용자 생활패턴 입력을 기반으로 점수를 계산한다."""

    def calculate_lifestyle_scores(self, lifestyle: dict) -> dict:
        """시간 유형/집 체류/외출/절약 민감도 점수를 계산한다."""
        scores = {
            "morning_score": 0,
            "daytime_score": 0,
            "night_score": 0,
            "irregular_score": 0,
            "stay_home_score": 0,
            "outing_score": 0,
            "cooling_need_score": 0,
            "saving_priority_score": 0,
            "saving_opportunity_score": 0,
        }

        # 시간 유형 점수
        mat = lifestyle.get("main_activity_time")
        if mat == "아침형":
            scores["morning_score"] += 3
        elif mat == "낮 활동":
            scores["daytime_score"] += 3
        elif mat == "야간 활동":
            scores["night_score"] += 3
        elif mat == "불규칙":
            scores["irregular_score"] += 3

        # 취침 시간대
        st = lifestyle.get("sleep_time")
        if st == "밤":
            scores["morning_score"] += 1
        elif st == "새벽":
            scores["night_score"] += 2
        elif st == "오전":
            scores["night_score"] += 3
        elif st == "불규칙":
            scores["irregular_score"] += 2

        # 집 체류 점수
        dhs = lifestyle.get("daytime_home_stay")
        if dhs == "거의 없음":
            scores["outing_score"] += 3
        elif dhs == "오후 잠깐":
            scores["outing_score"] += 1
            scores["daytime_score"] += 1
        elif dhs == "오후 오래":
            scores["stay_home_score"] += 2
        elif dhs == "종일 재택":
            scores["stay_home_score"] += 3

        # 더운 시간대 집 체류
        hths = lifestyle.get("hot_time_home_stay")
        if hths == "자주":
            scores["cooling_need_score"] += 2
        elif hths == "거의 항상":
            scores["cooling_need_score"] += 3

        # 외출 점수
        oa = lifestyle.get("outdoor_activity")
        if oa == "많음":
            scores["outing_score"] += 2
        elif oa == "보통":
            scores["outing_score"] += 1
        elif oa == "적음":
            scores["stay_home_score"] += 1

        return scores
