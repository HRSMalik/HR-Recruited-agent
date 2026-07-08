python version 3.11.13

run "pip install -r requirements.txt"

set these env variables

OPENAI_API_KEY=
LINKEDIN_EMAIL=
LINKEDIN_PASSWORD=

GOOGLE_FORM_URL=
GOOGLE_FORM_JD_ENTRY_ID=
GOOGLE_SHEETS_ID=
GOOGLE_SHEET_NAME=
GOOGLE_SHEET_JOB_ID_COLUMN=
GOOGLE_SHEET_CV_COLUMN=


SHORTLIST_INTERVAL_SECONDS=


SHORTLIST_INTERVAL_SECONDS=30

MONGODB_URI=""
MONGODB_DB=""

VAPI_API_KEY=
VAPI_ASSISTANT_ID=
VAPI_PHONE_NUMBER_ID=
VAPI_DEFAULT_COUNTRY_CODE=


after that enable google developer drive api from google console and place the credential.json file in a folder called .credentials

finally run the api entrypoint like so "uvicorn api:app --port 8000"

## Frontend (recruiter dashboard)

The React + TypeScript + Vite dashboard lives in `frontend/`. Run it against the backend:

    cd frontend
    npm install
    npm run dev            # http://localhost:5173

Point it at the API via `frontend/.env.local`:

    VITE_API_BASE_URL=http://localhost:8000
    VITE_API_KEY=<must match the backend API_KEY>

The FE authenticates with `Authorization: Bearer <VITE_API_KEY>`, so that key must equal the backend `API_KEY`, and the backend `CORS_ALLOWED_ORIGINS` must include `http://localhost:5173`.
