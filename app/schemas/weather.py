"""Weather schemas for hourly weather response.

Requirements: 3.1, 3.2
"""

from __future__ import annotations

import datetime as dt
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class WeatherTimeBlockSchema(BaseModel):
    time_range: Literal["새벽", "아침", "오전", "오후", "저녁", "밤"]
    temperature: float = Field(description="Temperature in °C, 1 decimal place")
    feels_like: float = Field(description="Feels-like temperature in °C, 1 decimal place")
    humidity: int = Field(ge=0, le=100, description="Humidity percentage")
    rain: bool = Field(description="Whether there is rain")
    heat_alert: bool = Field(description="True if temperature >= 35.0°C")

    model_config = ConfigDict(from_attributes=True)


class WeatherHourlyResponse(BaseModel):
    date: dt.date
    time_blocks: List[WeatherTimeBlockSchema]
    cached: bool = False

    model_config = ConfigDict(from_attributes=True)
