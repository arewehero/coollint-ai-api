from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정. 환경변수로 오버라이드 가능."""

    APP_ENV: str = "local"
    APP_NAME: str = "coollink-api"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://user:password@localhost:5432/coollink"

    # Weather
    OPENWEATHER_API_KEY: str = ""
    WEATHER_PROVIDER: str = "openweathermap"
    WEATHER_CACHE_TTL_SECONDS: int = 3600

    # AI / AWS
    AWS_REGION: str = "ap-northeast-2"
    BEDROCK_MODEL_ID: str = ""
    AI_TIMEOUT_SECONDS: int = 8
    AI_LOG_PAYLOAD: bool = False

    # Security
    INTERNAL_JOB_TOKEN: str = ""

    # CORS
    CORS_ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # Calculation defaults
    DEFAULT_ELECTRICITY_UNIT_PRICE: float = 150.0
    CO2_FACTOR_KG_PER_KWH: float = 0.4781
    TREE_ABSORPTION_KG_PER_YEAR: float = 6.6

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
