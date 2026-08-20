import csv
import io
import secrets
import string

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from .. import db
from ..content import CHARACTERISTICS
from ..models import CreateSessionRequest

router = APIRouter(prefix="/api/instructor", tags=["instructor"])


def _gen_code():
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


@router.post("/sessions")
def create_session(req: CreateSessionRequest):
    with db.get_conn() as conn:
        for _ in range(20):
            code = _gen_code()
            exists = conn.execute("SELECT 1 FROM sessions WHERE code = ?", (code,)).fetchone()
            if not exists:
                break
        else:
            raise HTTPException(500, "Could not generate a unique session code")

        cur = conn.execute(
            "INSERT INTO sessions (name, code, max_attempts) VALUES (?, ?, ?)",
            (req.name, code, req.max_attempts),
        )
        session_id = cur.lastrowid

    return _dashboard(session_id)


def _student_summary_rows(conn, session_id):
    students = [db.row_to_dict(r) for r in conn.execute(
        "SELECT * FROM students WHERE session_id = ? ORDER BY name", (session_id,)
    ).fetchall()]

    rows = []
    for s in students:
        attempts = conn.execute(
            "SELECT * FROM attempts WHERE student_id = ? ORDER BY attempt_number", (s["id"],)
        ).fetchall()
        attempts = [db.row_to_dict(a) for a in attempts]
        for a in attempts:
            a["criteria_result"] = db.loads(a["criteria_result"])
            a["is_final"] = bool(a["is_final"])
        final = next((a for a in attempts if a["is_final"]), None)
        rows.append({
            "student_id": s["id"],
            "student_name": s["name"],
            "attempts_used": len(attempts),
            "is_final": final is not None,
            "final_word_count": final["word_count"] if final else None,
            "final_draft": final["draft_text"] if final else None,
            "final_criteria": final["criteria_result"] if final else None,
        })
    return rows


def _dashboard(session_id):
    with db.get_conn() as conn:
        session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not session:
            raise HTTPException(404, "Session not found")
        session = db.row_to_dict(session)
        rows = _student_summary_rows(conn, session_id)

    struggle_counts = [0] * len(CHARACTERISTICS)
    finalized_count = 0
    for r in rows:
        if r["final_criteria"]:
            finalized_count += 1
            for i, c in enumerate(r["final_criteria"]):
                if c["status"] != "Pass":
                    struggle_counts[i] += 1

    struggle_stats = [
        {
            "characteristic": CHARACTERISTICS[i],
            "needs_work_count": struggle_counts[i],
            "needs_work_rate": (struggle_counts[i] / finalized_count) if finalized_count else None,
        }
        for i in range(len(CHARACTERISTICS))
    ]

    return {
        "session": session,
        "students": rows,
        "finalized_count": finalized_count,
        "struggle_stats": struggle_stats,
    }


@router.get("/sessions/{code}")
def get_session(code: str):
    with db.get_conn() as conn:
        row = conn.execute("SELECT id FROM sessions WHERE code = ?", (code.upper(),)).fetchone()
        if not row:
            raise HTTPException(404, "Session not found")
        session_id = row["id"]
    return _dashboard(session_id)


@router.get("/sessions/{code}/export.csv")
def export_csv(code: str):
    with db.get_conn() as conn:
        row = conn.execute("SELECT id, name FROM sessions WHERE code = ?", (code.upper(),)).fetchone()
        if not row:
            raise HTTPException(404, "Session not found")
        session_id = row["id"]
        rows = _student_summary_rows(conn, session_id)

    buf = io.StringIO()
    writer = csv.writer(buf)
    header = ["Student", "Attempts used", "Finalized", "Final word count", "Final mission statement"]
    header += [f"C{i+1}: {c}" for i, c in enumerate(CHARACTERISTICS)]
    writer.writerow(header)

    for r in rows:
        row_out = [
            r["student_name"],
            r["attempts_used"],
            "Yes" if r["is_final"] else "No",
            r["final_word_count"] if r["final_word_count"] is not None else "",
            r["final_draft"] or "",
        ]
        if r["final_criteria"]:
            row_out += [c["status"] for c in r["final_criteria"]]
        else:
            row_out += [""] * len(CHARACTERISTICS)
        writer.writerow(row_out)

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{code}_results.csv"'},
    )
