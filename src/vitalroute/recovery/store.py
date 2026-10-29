"""Durable run state and append-only evidence, backed by SQLite WAL."""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

def now():
    return datetime.now(UTC).isoformat()

class Store:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "recovery.sqlite"
        self.lock = threading.RLock()
        with self.db() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, created TEXT NOT NULL, updated TEXT NOT NULL,
                    status TEXT NOT NULL, document TEXT NOT NULL, request_key TEXT UNIQUE
                );
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
                    time TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS outbox (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL, kind TEXT NOT NULL,
                    created TEXT NOT NULL, status TEXT NOT NULL, document TEXT NOT NULL,
                    UNIQUE(run_id, kind)
                );
            """)

    @contextmanager
    def db(self):
        with self.lock:
            conn = sqlite3.connect(self.path, timeout=30)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def create(self, run, key=None):
        with self.db() as db:
            if key:
                row = db.execute("SELECT document FROM runs WHERE request_key=?", (key,)).fetchone()
                if row:
                    return json.loads(row[0]), False
            run.update(created=now(), updated=now())
            db.execute(
                "INSERT INTO runs VALUES(?,?,?,?,?,?)",
                (run["id"], run["created"], run["updated"], run["status"], json.dumps(run), key),
            )
        return run, True

    def get(self, rid):
        with self.db() as db:
            row = db.execute("SELECT document FROM runs WHERE id=?", (rid,)).fetchone()
        if not row:
            raise KeyError(rid)
        return json.loads(row[0])

    def update(self, rid, **changes):
        with self.db() as db:
            run = self.get(rid)
            run.update(changes, updated=now())
            db.execute(
                "UPDATE runs SET updated=?,status=?,document=? WHERE id=?",
                (run["updated"], run["status"], json.dumps(run), rid),
            )
        return run

    def event(self, rid, kind, title, **body):
        with self.db() as db:
            db.execute(
                "INSERT INTO events(run_id,time,kind,title,body) VALUES(?,?,?,?,?)",
                (rid, now(), kind, title, json.dumps(body, default=str)),
            )

    def events(self, rid, after=0):
        with self.db() as db:
            rows = db.execute(
                "SELECT * FROM events WHERE run_id=? AND seq>? ORDER BY seq", (rid, after)
            ).fetchall()
        return [{**dict(r), "body": json.loads(r["body"])} for r in rows]

    def list(self):
        with self.db() as db:
            rows = db.execute("SELECT document FROM runs ORDER BY created DESC LIMIT 200").fetchall()
        return [json.loads(r[0]) for r in rows]

    def decide(self, rid, digest, approve, actor):
        # Compare-and-set approval is bound to the exact tested code AND input digest.
        with self.lock:
            run = self.get(rid)
            if run["status"] != "awaiting_approval" or run["proposal"]["digest"] != digest:
                raise ValueError("Approval is stale or this run no longer awaits approval")
            return self.update(
                rid,
                status="approved" if approve else "rejected",
                approval={"actor": actor, "time": now(), "digest": digest, "approved": approve},
            )

    def queue_email(self, rid, kind, doc):
        with self.db() as db:
            db.execute(
                "INSERT OR IGNORE INTO outbox VALUES(?,?,?,?,?,?)",
                (f"{rid}-{kind}", rid, kind, now(), "queued", json.dumps(doc)),
            )

    def emails(self, rid=None):
        with self.db() as db:
            rows = db.execute(
                "SELECT * FROM outbox" + (" WHERE run_id=?" if rid else "") + " ORDER BY created",
                (rid,) if rid else (),
            ).fetchall()
        return [{**dict(r), "document": json.loads(r["document"])} for r in rows]

    def email_status(self, ident, status, **receipt):
        with self.db() as db:
            row = db.execute("SELECT document FROM outbox WHERE id=?", (ident,)).fetchone()
            doc = json.loads(row[0])
            doc.update(receipt)
            db.execute("UPDATE outbox SET status=?,document=? WHERE id=?", (status, json.dumps(doc), ident))

    def claim_email(self, ident):
        with self.db() as db:
            return (
                db.execute(
                    "UPDATE outbox SET status='sending' WHERE id=? AND status='queued'", (ident,)
                ).rowcount
                == 1
            )
