from pydantic import BaseModel


class GoalInfo(BaseModel):
    monthly_electricity_bill: int
    monthly_goal_bill: int | None = None
    required_monthly_saving_krw: int | None = None
    current_projected_saving_krw: int | None = None
    on_track: bool | None = None


class SavingSummaryResponse(BaseModel):
    period: str
    period_start: str
    period_end: str
    completed_action_count: int
    total_action_count: int
    total_saving_krw: int
    total_possible_saving_krw: int
    total_energy_saving_kwh: float
    total_possible_energy_saving_kwh: float
    total_co2_reduction_kg: float
    total_possible_co2_reduction_kg: float
    monthly_projected_saving_krw: int | None = None
    goal: GoalInfo | None = None
    message: str | None = None


class CalendarDaySchema(BaseModel):
    date: str
    completed_action_count: int
    total_saving_krw: int
    total_co2_reduction_kg: float


class MonthlyTotal(BaseModel):
    saving_krw: int
    energy_saving_kwh: float
    co2_reduction_kg: float


class CalendarResponse(BaseModel):
    month: str
    days: list[CalendarDaySchema]
    monthly_total: MonthlyTotal
