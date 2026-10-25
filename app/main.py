import os
import socket

import psycopg
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

DATABASE_URL = os.environ.get("DATABASE_URL", "")
MAX_NOTE_LENGTH = 500

app = FastAPI(title="Lab Notes")
templates = Jinja2Templates(directory="templates")

# The table is created on the first successful connection, not at startup.
# After a reboot Docker may start the web container before Postgres is ready,
# so the app must not crash just because the database is not up yet.
_schema_ready = False


def get_conn():
    global _schema_ready
    conn = psycopg.connect(DATABASE_URL, connect_timeout=3)
    if not _schema_ready:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                body TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.commit()
        _schema_ready = True
    return conn


def render(request: Request, notes=None, error=None, status_code=200):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "notes": notes or [],
            "error": error,
            # Shares the host's UTS namespace (uts: host in Compose),
            # so this is the EC2 instance's hostname, not the container ID.
            "served_by": socket.gethostname(),
            "max_length": MAX_NOTE_LENGTH,
        },
        status_code=status_code,
    )


@app.get("/")
def index(request: Request):
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT body, created_at FROM notes ORDER BY id DESC LIMIT 50"
            ).fetchall()
    except psycopg.Error:
        return render(
            request,
            error="Can't reach the database. Check that the db container is running.",
            status_code=503,
        )
    notes = [{"body": r[0], "created_at": r[1]} for r in rows]
    return render(request, notes=notes)


@app.post("/notes")
def add_note(request: Request, body: str = Form("")):
    body = body.strip()
    if not body or len(body) > MAX_NOTE_LENGTH:
        return RedirectResponse("/", status_code=303)
    try:
        with get_conn() as conn:
            conn.execute("INSERT INTO notes (body) VALUES (%s)", (body,))
    except psycopg.Error:
        return render(
            request,
            error="The note wasn't saved because the database is unreachable.",
            status_code=503,
        )
    # Post/Redirect/Get: refreshing the page won't resubmit the form.
    return RedirectResponse("/", status_code=303)


@app.get("/health")
def health():
    # The load balancer calls this. 503 marks the instance unhealthy,
    # and the Auto Scaling Group replaces it.
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
    except psycopg.Error:
        return JSONResponse({"status": "db_unreachable"}, status_code=503)
    return {"status": "ok", "host": socket.gethostname()}
