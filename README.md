# CoolLink AI API

탄소중립 및 전기요금 절약 행동 추천 FastAPI 백엔드입니다.

현재 AI 담당자 코드가 아직 없으므로 `AI_PROVIDER=mock` 기준의
`MockAIClient`/`FallbackAIClient`로 생활유형 분석과 추천 문구 생성을
대체합니다. AWS Bedrock 실제 호출은 포함하지 않습니다.

## Tech Stack

- FastAPI
- Python
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic
- pytest
- Mock AI Gateway

## Setup & Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Swagger:

- http://localhost:8000/docs

## AI Gateway

```env
AI_PROVIDER=mock
AI_TIMEOUT_SECONDS=8
AI_LOG_PAYLOAD=false
```

- `MockAIClient` returns deterministic mock lifestyle analysis and action copy.
- `FallbackAIClient` returns template-based copy when AI output is invalid or
  unavailable.
- AI responses are validated with Pydantic schemas in `app/schemas/ai.py`.
- AI-generated copy never creates or changes saving, kWh, or CO2 values.

Run lightweight tests with:

```bash
python -m pytest -q
```

## Major APIs

- `GET /health`
- `POST /api/v1/users/anonymous` (shared user/profile domain dependency)
- `PUT /api/v1/profile` (shared user/profile domain dependency)
- `POST /api/v1/ai/lifestyle-analysis`
- `POST /api/v1/recommendations/daily`
- `GET /api/v1/recommendations/daily`
- `PATCH /api/v1/recommendations/actions/{action_id}`
- `GET /api/v1/savings/summary`
- `GET /api/v1/savings/calendar`
- `POST /api/v1/internal/jobs/generate-daily-recommendations`

## Notes

- The migration assumes the shared `users` table already exists.
- No AWS Bedrock, SMS, Kakao, admin, vulnerable-group, or health-info code is
  included in this phase.
