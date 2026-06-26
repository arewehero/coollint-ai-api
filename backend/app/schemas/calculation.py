from pydantic import BaseModel, Field


class EstimateRequest(BaseModel):
    ac_power_watt: int | None = Field(None, gt=0, le=5000)
    room_size: str | None = None
    current_temperature_setting: float = Field(..., ge=18, le=30)
    target_temperature_setting: float = Field(..., ge=18, le=30)
    usage_hours: float = Field(..., ge=0, le=24)
    electricity_unit_price: float = Field(150, ge=1, le=1000)


class EnergyEstimate(BaseModel):
    energy_kwh: float
    cost_krw: int


class SavingEstimate(BaseModel):
    energy_kwh: float
    cost_krw: int
    co2_kg: float


class AssumptionsInfo(BaseModel):
    ac_power_watt_source: str
    current_temperature_coefficient: float
    target_temperature_coefficient: float
    co2_factor_kg_per_kwh: float


class EstimateResponse(BaseModel):
    current: EnergyEstimate
    target: EnergyEstimate
    saving: SavingEstimate
    assumptions: AssumptionsInfo
