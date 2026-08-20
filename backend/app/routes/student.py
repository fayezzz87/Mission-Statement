from fastapi import APIRouter, HTTPException

from .. import db, agent
from ..content import SCENARIO, CHARACTERISTICS, WORD_COUNT_GUIDELINE
from ..models import JoinRequest, DraftRequest, FinalizeRequest

router = APIRouter(prefix="/api/student", tags=["student"])


def _parse_attempt(row):
    d = db.row_to_dict(row)
    if d is None:
        return None
    d["criteria_result"] = db.loads(d["criteria_result"])
    d["persona_reactions"] = db.loads(d["persona_reactions"])
    d["is_final"] = bool(d["is_final"])
    return d


def _get_student_session(conn, student_id):
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        raise HTTPException(404, "Student not found")
    student = db.row_to_dict(student)
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (student["session_id"],)).fetchone()
    session = db.row_to_dict(session)
    return student, session


@router.post("/join")
def join(req: JoinRequest):
    session_code = req.session_code.strip().upper()
    student_name = req.student_name.strip()
    if not student_name:
        raise HTTPException(400, "Name is required")

    with db.get_conn() as conn:
        session = conn.execute("SELECT * FROM sessions WHERE code = ?", (session_code,)).fetchone()
        if not session:
            raise HTTPException(404, "No assignment found with that code")
        session = db.row_to_dict(session)

        student = conn.execute(
            "SELECT * FROM students WHERE session_id = ? AND name = ?", (session["id"], student_name)
        ).fetchone()
        if student:
            student = db.row_to_dict(student)
        else:
            cur = conn.execute(
                "INSERT INTO students (session_id, name) VALUES (?, ?) RETURNING id", (session["id"], student_name)
            )
            student = {"id": cur.lastrowid, "session_id": session["id"], "name": student_name}

    return {"student_id": student["id"], "student_name": student["name"], "session_code": session_code}


@router.get("/{student_id}/state")
def state(student_id: int):
    with db.get_conn() as conn:
        student, session = _get_student_session(conn, student_id)
        attempts = [
            _parse_attempt(r)
            for r in conn.execute(
                "SELECT * FROM attempts WHERE student_id = ? ORDER BY attempt_number", (student_id,)
            ).fetchall()
        ]

    is_final = any(a["is_final"] for a in attempts)
    attempts_remaining = max(0, session["max_attempts"] - len(attempts)) if not is_final else 0

    return {
        "student": {"id": student["id"], "name": student["name"]},
        "session": {"name": session["name"], "code": session["code"], "max_attempts": session["max_attempts"]},
        "scenario": SCENARIO,
        "characteristics": CHARACTERISTICS,
        "word_count_guideline": WORD_COUNT_GUIDELINE,
        "attempts": attempts,
        "is_final": is_final,
        "attempts_remaining": attempts_remaining,
    }


@router.post("/{student_id}/attempts")
async def submit_attempt(student_id: int, req: DraftRequest):
    draft_text = req.draft_text.strip()
    if not draft_text:
        raise HTTPException(400, "Draft text is required")

    with db.get_conn() as conn:
        student, session = _get_student_session(conn, student_id)
        existing = conn.execute(
            "SELECT * FROM attempts WHERE student_id = ? ORDER BY attempt_number", (student_id,)
        ).fetchall()
        existing = [_parse_attempt(r) for r in existing]

        if any(a["is_final"] for a in existing):
            raise HTTPException(400, "This assignment has already been finalized")
        if len(existing) >= session["max_attempts"]:
            raise HTTPException(400, "No attempts remaining")

        attempt_number = len(existing) + 1

    feedback = await agent.get_all_feedback(draft_text)
    is_final = 1 if attempt_number >= session["max_attempts"] else 0

    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO attempts (student_id, attempt_number, draft_text, word_count, "
            "criteria_result, persona_reactions, is_final) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                student_id, attempt_number, draft_text, feedback["word_count"],
                db.dumps(feedback["criteria"]), db.dumps(feedback["personas"]), is_final,
            ),
        )
        row = conn.execute(
            "SELECT * FROM attempts WHERE student_id = ? AND attempt_number = ?",
            (student_id, attempt_number),
        ).fetchone()

    return _parse_attempt(row)


@router.post("/{student_id}/finalize")
def finalize(student_id: int, req: FinalizeRequest):
    with db.get_conn() as conn:
        student, session = _get_student_session(conn, student_id)
        latest = conn.execute(
            "SELECT * FROM attempts WHERE student_id = ? ORDER BY attempt_number DESC LIMIT 1",
            (student_id,),
        ).fetchone()
        if not latest:
            raise HTTPException(400, "No attempts to finalize")
        latest = _parse_attempt(latest)
        if latest["is_final"]:
            raise HTTPException(400, "Already finalized")
        if latest["attempt_number"] != req.attempt_number:
            raise HTTPException(400, "Only the latest attempt can be finalized")

        conn.execute("UPDATE attempts SET is_final = 1 WHERE id = ?", (latest["id"],))
        row = conn.execute("SELECT * FROM attempts WHERE id = ?", (latest["id"],)).fetchone()

    return _parse_attempt(row)


@router.get("/{student_id}/summary")
def summary(student_id: int):
    with db.get_conn() as conn:
        student, session = _get_student_session(conn, student_id)
        attempts = [
            _parse_attempt(r)
            for r in conn.execute(
                "SELECT * FROM attempts WHERE student_id = ? ORDER BY attempt_number", (student_id,)
            ).fetchall()
        ]

    final_attempt = next((a for a in attempts if a["is_final"]), None)
    if not final_attempt:
        raise HTTPException(400, "This assignment has not been finalized yet")

    return {
        "student_name": student["name"],
        "session_name": session["name"],
        "attempts": attempts,
        "final_attempt": final_attempt,
    }
