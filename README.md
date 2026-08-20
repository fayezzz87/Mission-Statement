# Mission Statement Studio

A short, single-session assignment tool: students write a mission statement
for a fictional pizza company ("Slice Co.") and get feedback from 4 AI
department personas (CFO, COO, Legal/Compliance, HR/Culture) plus a neutral
criteria evaluator, iterating over a few attempts before finalizing.

The Anthropic API key lives only in `backend/.env` and is never sent to the
browser. Data is stored in Postgres (a free [Neon](https://neon.tech)
database in production), not a local file, so it survives restarts and
redeploys without needing a paid persistent disk.

## Setup

```powershell
python -m venv venv
venv\Scripts\pip install -r backend\requirements.txt
```

`backend/.env` needs two values (git-ignored):
```
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://user:password@host/dbname
```
`DATABASE_URL` is the connection string from your Neon project dashboard.
Local dev and production point at the same Neon database unless you create
a separate Neon project for local testing.

## Run

```powershell
venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend/app --port 8000
```

(`--reload-dir backend/app` scopes the auto-reload watcher to source code
only, so editing files doesn't trigger spurious restarts.)

Open **http://localhost:8000**.

- **Instructor**: *I'm the instructor* → create an assignment (set max
  attempts) → share the 6-character code → watch the dashboard fill in as
  students submit → export to CSV.
- **Students**: *I'm a student* → join with the code + your name → write a
  draft → *Get feedback* (calls all 5 AI reviewers in parallel) → revise or
  *Submit this as my final answer* → one-page summary (printable to PDF via
  the browser's print dialog).

## How it's built

- `backend/app/content.py` — the scenario text and the 5 required
  characteristics (fixed order — the evaluator's tool schema references them
  by index, so don't reorder without updating `agent.py` too).
- `backend/app/agent.py` — 5 concurrent Claude calls per "Get Feedback"
  click: 4 in-character department personas (freeform 2-4 sentence
  reactions) and one neutral rubric-checking evaluator (structured pass/needs
  -work + one sentence per characteristic, via forced tool use). Word count is
  computed in Python, not trusted to the model.
- `backend/app/db.py` — a thin wrapper so route code can call
  `conn.execute("... ? ...", params)` the same way whether the driver
  underneath is sqlite-style or (as of the Neon migration) psycopg2; it
  translates `?` → `%s` and captures `RETURNING id` into `.lastrowid`.
- `backend/app/routes/student.py` — join, state, submit attempt (auto-
  finalizes on the last allowed attempt), finalize early, one-page summary.
- `backend/app/routes/instructor.py` — session create/dashboard (including
  which characteristic students most often "Needs Work" on) and CSV export.
- `frontend/` — plain HTML/CSS/JS, no build step.

## Notes

- Attempts are capped per assignment (default 3, instructor-configurable);
  the last allowed attempt auto-finalizes so a student can't get stuck.

## Deploying to Render

`render.yaml` defines a **free** Python web service — no persistent disk
needed since data lives in Neon Postgres instead.

1. Create a free Neon project at [neon.tech](https://neon.tech) (no credit
   card) and copy its connection string.
2. Push this repo to GitHub.
3. In Render: **New +** → **Blueprint** → select the repo. Render reads
   `render.yaml` automatically.
4. When prompted, paste `ANTHROPIC_API_KEY` and `DATABASE_URL` (the Neon
   connection string) as env vars directly in Render's dashboard — never
   commit either value.
5. Deploy. Render gives you a stable `https://*.onrender.com` URL.

Notes:
- The free web service plan spins down after ~15 minutes idle and takes
  ~30s to wake on the next request — fine for a classroom tool, just expect
  a slow first load if nobody's used it in a while. Because data now lives
  in Neon rather than on the web service's own filesystem, this spin-down
  no longer risks losing data.
- Neon's free tier: 0.5GB storage, 100 compute-hours/month, database
  compute scales to zero after 5 minutes idle (it wakes automatically on
  the next query, adding a brief delay). Plenty for a single-assignment
  classroom tool.
- History: this originally ran on Render's free plan with SQLite on the
  local filesystem, which turned out to get wiped on ordinary spin-down/
  wake, not just explicit redeploys. Then briefly considered a paid Render
  disk (Starter plan) before settling on the free Neon route instead.
