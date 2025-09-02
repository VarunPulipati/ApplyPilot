ApplyPilot

A developer-friendly autopilot for job applications.

Imports jobs from supported sources (✅ Greenhouse; more coming).

Generates answers to application questions using Gemini (free-tier friendly).

Uploads a resume (your static PDF or an AI-tailored resume).

Fills & submits forms automatically (playback via Chromium).

Tracks every submission in applications.xlsx (+ keeps a leads list in leads.xlsx).

MVP focuses on Greenhouse roles. The architecture is modular so we can plug in Lever/Workday/LinkedIn later.

Table of contents

Features

Folder layout

Prerequisites

Quickstart

Configuration

Core workflow (manual)

Batch autopilot

Excel outputs

AI & Answering

Troubleshooting

Roadmap

License

Features

🔎 Source importers: Import job postings from Greenhouse boards.

🧠 AI assistance: Drafts answers for free-text questions using Gemini, grounded in your profile + QABank + the JD.

🧾 Resumes:

Static: upload and reuse your master PDF (recommended for consistency).

AI: optional HTML→PDF resume tailored to the JD.

🖱️ One-click apply: Opens the application form, uploads the resume, fills fields, answers questions, submits.

📒 Tracking: Appends every successful submission to applications.xlsx; keeps a picked-jobs list in leads.xlsx.

🧱 Safe “simulate” mode: Preview resumes/questions/answers before any real submit.

Folder layout
ApplyPilot/
app/
routes/ # FastAPI endpoints
services/ # connectors, AI, doc-gen, batching, tracker
templates/ # resume.html.j2 (for AI resume mode)
models.py # SQLAlchemy models (Job, Application, Profile, QABank)
database.py # DB engine/session
config.py # Settings (paths, DB url, etc.)
main.py # FastAPI entrypoint
migrations/ # Alembic migrations
storage/
docs/ # generated AI resume PDFs
resumes/ # uploaded static resumes
applications.xlsx # (created at runtime)
leads.xlsx # (created at runtime)
alembic.ini
requirements.txt
README.md
.env

Prerequisites

Python 3.12+

Chrome/Chromium (Playwright will install a bundled Chromium)

A Google AI Studio API key (Gemini) — free tier available

Quickstart

# 1) Clone & enter

git clone https://github.com/VarunPulipati/ApplyPilot.git
cd ApplyPilot

# 2) Create & activate venv

python -m venv .venv
.venv\Scripts\activate # (Windows)

# 3) Install deps

pip install -r requirements.txt

# 4) Install Playwright (Chromium)

python -m playwright install chromium

# 5) Configure Alembic DB URL (sqlite)

# Open alembic.ini and set:

# sqlalchemy.url = sqlite:///./local.db

# 6) Run DB migrations

alembic upgrade head

# 7) Set Gemini key (PowerShell example)

setx GEMINI_API_KEY "<YOUR_KEY>"

# Close/reopen terminal or set for current session:

$env:GEMINI_API_KEY = "<YOUR_KEY>"

# 8) Run API

uvicorn app.main:app --reload

# 9) Open docs

# http://127.0.0.1:8000/docs

If you already have GOOGLE_API_KEY set, the app will use it; otherwise it looks for GEMINI_API_KEY.

Configuration

app/config.py provides safe defaults and path helpers:

doc_out_dir – where AI resume PDFs are written (storage/docs)

resumes_dir – where uploaded static resumes are saved (storage/resumes)

template_dir – Jinja templates for AI resume (templates)

database_url – default sqlite:///./local.db

Override in .env if you like:

DATABASE_URL=sqlite:///./local.db
DOC_OUT_DIR=storage/docs
RESUMES_DIR=storage/resumes
TEMPLATE_DIR=templates

# Either of these works:

GEMINI_API_KEY=your_key_here

# or

GOOGLE_API_KEY=your_key_here

Core workflow (manual)

Create a profile
POST /profiles

{
"name": "Varun S",
"email": "me@example.com",
"phone": "+1-555-000-0000",
"location": "Dallas, TX",
"skills_csv": "Python, SQL, Airflow, Spark, Snowflake",
"resume_path": "" // (leave empty for AI resume or upload a static PDF next)
}

Upload your master PDF resume (optional but recommended)
POST /profiles/{id}/resume (multipart file)
→ updates Profile.resume_path under storage/resumes/….

Import jobs (Greenhouse)
POST /sources/import-company

{ "source": "greenhouse", "company": "datadog" }

The company is the board slug from the URL: https://boards.greenhouse.io/<slug>.

List jobs
GET /jobs → pick a job_id.

Preview an application (safe; doesn’t submit)
POST /apply

{
"job_id": 123,
"profile_id": 1,
"simulate": true,
"resume_mode": "static" // or "ai"
}

Returns:

resume_pdf (path used/generated),

found_questions (scraped),

draft_answers (Gemini).

Submit for real
Same endpoint with "simulate": false. Chromium opens, fills, submits, and returns a confirmation if available. A new row is appended to applications.xlsx.

Batch autopilot

One call to preview or apply N jobs automatically.

POST /autopilot/run

{
"profile_id": 1,
"limit": 10, // how many unapplied jobs to process
"resume_mode": "static", // "static" uses your uploaded PDF; "ai" builds a tailored PDF per job
"submit": false, // false = preview, true = actually submit
"delay_seconds": 2.0 // polite delay between jobs
}

What it does:

Picks the latest N jobs not already applied.

Writes them into leads.xlsx (sheet “Leads”).

For each job: fetches JD → makes resume → scrapes questions → drafts answers → (optionally) submits.

On successful submit: creates a DB Application and appends a row in applications.xlsx.

Return JSON includes per-job status (previewed / submitted / failed), resume_pdf, found_questions, draft_answers, and confirmation (if submitted).

Excel outputs

leads.xlsx (sheet Leads): the jobs picked for the batch.

Columns: company, title, job_url, ats_type, imported_at

applications.xlsx (sheet Applications): one row per successful submission.

Columns: company, role, date_applied, job_url, source, ats_type, confirmation_number, status, resume_version, notes

Both files are created on first use if missing.

AI & Answering

Model: Gemini 2.5 Flash via google-genai.

Inputs: your Profile (contact + skills), QABank (experience bullets / answers you trust), and JD text (scraped).

Output: concise, role-relevant answers mapped to scraped labels/placeholders from the form.

Resume modes:

static: attach your uploaded PDF (recommended for consistent ATS parsing).

ai: render a tailored HTML→PDF resume using templates/resume.html.j2.

Tip: keep your best bullets in QABank; AI reuses & adapts them rather than inventing new claims.

Troubleshooting

Swagger says 422 JSON decode error
— Remove comments/trailing commas in the example JSON. Swagger requires strict JSON.

Unsupported source when importing
— Use lowercase {"source":"greenhouse","company":"slug"}.

python-multipart required
— pip install python-multipart (for file uploads).

Playwright NotImplementedError on Windows
— Already handled in doc_gen.html_to_pdf by enforcing Proactor loop. Make sure to run:

python -m playwright install chromium

TemplateNotFound: resume.html.j2 (AI mode)
— Ensure templates/resume.html.j2 exists. A minimal template is included in the repo docs—customize freely.

GEMINI_API_KEY is required
— Set GEMINI_API_KEY (or GOOGLE_API_KEY) and restart your shell:

setx GEMINI_API_KEY "<YOUR_KEY>"
$env:GEMINI_API_KEY = "<YOUR_KEY>" # current PowerShell session

No questions found
— Many forms only ask for structured fields (name, email, phone, resume). That’s fine; the bot still applies. For Datadog/other wrappers, the connector jumps to Greenhouse’s embed form; if a specific page is unusual, open an issue with the URL.

Roadmap

Additional connectors: Lever, Workday, SmartRecruiters.

LinkedIn job ingestion + apply.

Headless submit toggle & per-site capchas/login helpers.

QABank CRUD endpoints & import/export.

Multi-profile support & prioritization rules.

Retry policies & richer confirmation scraping.

License

MIT (add your LICENSE file if you want to use MIT; otherwise edit this section).

Notes

This project automates interactions with third-party sites you control via your browser. Be mindful of the applicable terms of service for each site and use the “simulate” mode to confirm behavior before enabling submissions.

Keep the resume factual. AI drafts should never fabricate work history or credentials.
