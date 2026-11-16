"""Human feedback = the learning signal. (The dashboard's Review page does the same thing.)

    python feedback.py list                      # pending investigations
    python feedback.py confirm 3                 # agent was right
    python feedback.py correct 3 ECOSYSTEM_WIDE "serde+tokio+syn all fell together"
    python feedback.py stats
"""
import sys

import config
import memory
from db import connect


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "list"
    if cmd == "list":
        for r in connect().execute("SELECT * FROM investigations WHERE status='pending' ORDER BY id"):
            print(f"#{r['id']} {r['entity']} {r['event_date']}  -> {r['hypothesis']} "
                  f"({r['confidence']})\n   evidence: {r['evidence']}\n")
    elif cmd == "confirm":
        memory.confirm(int(argv[1]))
        print("confirmed.")
    elif cmd == "correct":
        causes = config.load()["causes"]
        if argv[2] not in causes:
            sys.exit(f"cause must be one of {list(causes)}")
        memory.correct(int(argv[1]), argv[2], " ".join(argv[3:]))
        print("corrected; lesson stored.")
    elif cmd == "stats":
        print(memory.track_record())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
