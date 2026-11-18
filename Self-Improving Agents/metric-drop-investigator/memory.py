"""The agent's memory: lessons + graded investigations. Used by tools, CLI, and dashboard."""
from datetime import datetime, timezone

from db import connect


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ lessons
def list_lessons(limit: int | None = None) -> list[dict]:
    q = "SELECT * FROM lessons ORDER BY id DESC" + (f" LIMIT {int(limit)}" if limit else "")
    return [dict(r) for r in connect().execute(q)]


def add_lesson(situation: str, lesson: str, source: str = "manual") -> None:
    con = connect()
    con.execute("INSERT INTO lessons(ts,situation,lesson,source) VALUES (?,?,?,?)",
                (_now(), situation, lesson, source))
    con.commit()


def delete_lesson(lesson_id: int) -> None:
    con = connect()
    con.execute("DELETE FROM lessons WHERE id=?", (lesson_id,))
    con.commit()


# ------------------------------------------------------------------ grading
def confirm(inv_id: int) -> None:
    con = connect()
    con.execute("UPDATE investigations SET status='confirmed', true_cause=hypothesis, graded_at=? WHERE id=?",
                (_now(), inv_id))
    r = con.execute("SELECT * FROM investigations WHERE id=?", (inv_id,)).fetchone()
    con.commit()
    add_lesson(f"{r['hypothesis']} confirmed",
               f"Human confirmed {r['hypothesis']} for {r['entity']} on {r['event_date']}. "
               f"Evidence pattern that worked: {r['evidence']}", "feedback")


def correct(inv_id: int, true_cause: str, note: str = "") -> None:
    con = connect()
    r = con.execute("SELECT * FROM investigations WHERE id=?", (inv_id,)).fetchone()
    con.execute("UPDATE investigations SET status='corrected', true_cause=?, feedback_note=?, graded_at=? WHERE id=?",
                (true_cause, note, _now(), inv_id))
    con.commit()
    add_lesson(f"{r['entity']} {r['event_date']}: I said {r['hypothesis']}, truth was {true_cause}",
               f"I wrongly concluded {r['hypothesis']} (evidence: {r['evidence']}). "
               f"Truth: {true_cause}. Human note: {note}", "feedback")


def track_record() -> dict:
    r = connect().execute(
        "SELECT SUM(status='confirmed') ok, SUM(status='corrected') wrong, SUM(status='pending') pending "
        "FROM investigations").fetchone()
    ok, wrong, pending = (r["ok"] or 0), (r["wrong"] or 0), (r["pending"] or 0)
    graded = ok + wrong
    return {"confirmed": ok, "corrected": wrong, "pending": pending, "graded": graded,
            "accuracy": (ok / graded) if graded else None}


def outcomes_by_cause() -> list[dict]:
    return [dict(r) for r in connect().execute(
        "SELECT COALESCE(true_cause,hypothesis) cause, status, COUNT(*) n FROM investigations "
        "WHERE status!='pending' GROUP BY 1,2 ORDER BY n DESC")]


# --------------------------------------------------------- what the agent sees
def memory_block(max_lessons: int) -> str:
    """Plain-text memory shown to the agent (used for 'inject' mode and the recall tool)."""
    lessons = list_lessons(max_lessons)
    tr = track_record()
    lines = []
    if lessons:
        lines.append("Lessons from past investigations (newest first):")
        lines += [f"- [{l['source']}] {l['situation'][:120]}: {l['lesson'][:300]}" for l in lessons]
    else:
        lines.append("No lessons yet.")
    lines.append(f"Track record: {tr['confirmed']} confirmed, {tr['corrected']} corrected by humans.")
    return "\n".join(lines)
