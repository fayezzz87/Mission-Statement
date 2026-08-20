# Mission Statement Studio

A short, single-session assignment tool: students write a mission statement
for a fictional pizza company ("Slice Co.") and get feedback from 4 AI
department personas (CFO, COO, Legal/Compliance, HR/Culture) plus a neutral
criteria evaluator, iterating over a few attempts before finalizing.

The Anthropic API key lives only in `backend/.env` and is never sent to the
browser.

## Setup

```powershell
python -m venv venv
venv\Scripts\pip install -r backend\requirements.txt
```

`backend/.env` already contains `ANTHROPIC_API_KEY=...` (git-ignored).

## Run

```powershell
venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend/app --port 8000
```

(`--reload-dir backend/app` scopes the auto-reload watcher to source code only —
without it, uvicorn watches the whole project including `backend/data.db`, so
every database write during use would trigger a server restart.)

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
- `backend/app/routes/student.py` — join, state, submit attempt (auto-
  finalizes on the last allowed attempt), finalize early, one-page summary.
- `backend/app/routes/instructor.py` — session create/dashboard (including
  which characteristic students most often "Needs Work" on) and CSV export.
- `frontend/` — plain HTML/CSS/JS, no build step.

## Notes

- Attempts are capped per assignment (default 3, instructor-configurable);
  the last allowed attempt auto-finalizes so a student can't get stuck.

## Deploying to Render

`render.yaml` in the project root defines the service: a free Python web
service plus a small persistent disk (mounted at `/var/data`, via the
`DATA_DIR` env var) so student submissions survive restarts/redeploys.

1. Push this repo to GitHub.
2. In Render: **New +** → **Blueprint** → select the repo. Render reads
   `render.yaml` automatically.
3. When prompted, paste your Anthropic API key as the `ANTHROPIC_API_KEY`
   env var (from `backend/.env` — never commit that file).
4. Deploy. Render gives you a stable `https://*.onrender.com` URL.

Note: the free plan spins down after ~15 minutes idle and takes ~30s to
wake up on the next request — fine for a classroom tool, just expect a
slow first load if nobody's used it in a while.
