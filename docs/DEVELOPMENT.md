# Development

## Prerequisites

- Windows 11, Node.js 20.9+, npm.
- Python 3.11 recommended. No GPU or model download is needed.

## Backend

From `backend`, create and activate a virtual environment, install `requirements.txt`, copy `.env.example` to `.env`, and run `uvicorn app.main:app --reload`. The SQLite database and upload directory are relative to the backend working directory by default. The service listens at `http://localhost:8000`; interactive docs are at `/docs`.

## Frontend

From project root, run `npm install`, copy `.env.example` to `.env.local`, then `npm run dev`. The app listens at `http://localhost:3000`. Set `NEXT_PUBLIC_API_URL` before starting the frontend if the API is elsewhere.

## Quality checks

Run `npm run typecheck`, `npm run lint`, and `npm run build` for frontend checks. Backend tests use `python -m pytest` from the backend directory. Run the service and exercise `/api/v1/health`, image upload, and research endpoints for integration checks.

## Troubleshooting

- Frontend network errors: confirm the API is running and `NEXT_PUBLIC_API_URL` is correct.
- CORS errors: set backend `FRONTEND_ORIGIN` to the exact browser origin, then restart.
- PowerShell blocks virtualenv activation: use `py -3.11 -m venv .venv`; alternatively invoke `.venv\Scripts\python.exe -m uvicorn app.main:app --reload` without activation.
- Upload rejected: only real JPEG, PNG, or WEBP images up to 10 MB and 40 megapixels are accepted.
