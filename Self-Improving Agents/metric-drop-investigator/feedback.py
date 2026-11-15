"""Human feedback = the learning signal. Grade the agent's investigations.

    python feedback.py list                      # pending investigations
    python feedback.py confirm 3                 # agent was right
    python feedback.py correct 3 ECOSYSTEM_WIDE "serde+tokio+syn all fell together"
    python feedback.py stats

Corrections are turned into lessons the agent reads at the start of every run.
"""
import sys
from datetime import datetime, timezone

from db import CAUSES, connect


def main(argv: list[str]) -> None:
    con = connect()
    cmd = argv[0] if argv else "list"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if cmd == "list":
        for r in con.execute("SELECT * FROM investigations WHERE status='pending' ORDER BY id"):
            print(f"#{r['id']} {r['crate']} {r['event_date']}  -> {r['hypothesis']} "
                  f"({r['confidence']})\n   evidence: {r['evidence']}\n")
    elif cmd == "confirm":
        i = int(argv[1])
        con.execute("UPDATE investigations SET status='confirmed', true_cause=hypothesis WHERE id=?", (i,))
        r = con.execute("SELECT * FROM investigations WHERE id=?", (i,)).fetchone()
        con.execute("INSERT INTO lessons(ts,situation,lesson,source) VALUES (?,?,?,'feedback')",
                    (now, f"{r['hypothesis']} confirmed", f"Human confirmed {r['hypothesis']} for {r['crate']} "
                     f"on {r['event_date']}. Evidence pattern that worked: {r['evidence']}", ))
        con.commit()
        print("confirmed.")
    elif cmd == "correct":
        i, cause, note = int(argv[1]), argv[2], " ".join(argv[3:])
        if cause not in CAUSES:
            sys.exit(f"cause must be one of {list(CAUSES)}")
        r = con.execute("SELECT * FROM investigations WHERE id=?", (i,)).fetchone()
        con.execute("UPDATE investigations SET status='corrected', true_cause=?, feedback_note=? WHERE id=?",
                    (cause, note, i))
        con.execute("INSERT INTO lessons(ts,situation,lesson,source) VALUES (?,?,?,'feedback')",
                    (now, f"{r['crate']} {r['event_date']}: I said {r['hypothesis']}, truth was {cause}",
                     f"I wrongly concluded {r['hypothesis']} (evidence: {r['evidence']}). "
                     f"Truth: {cause}. Human note: {note}"))
        con.commit()
        print("corrected; lesson stored.")
    elif cmd == "stats":
        for r in con.execute("SELECT status, COUNT(*) n FROM investigations GROUP BY status"):
            print(r["status"], r["n"])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
