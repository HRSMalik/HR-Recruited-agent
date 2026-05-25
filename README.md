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

after that enable google developer drive api from google console and place the credential.json file in a folder called .credentials

finally run the app.py file like so "uvicorn app:app"