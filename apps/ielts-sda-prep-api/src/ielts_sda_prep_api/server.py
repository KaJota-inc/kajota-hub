"""FastAPI server for the IELTS × SD × PhD prep sync backend.

Mount point behind kajota-hub: ``/ielts-sda-prep-api/*``. Caddy's
``handle_path`` strips the prefix, so the app sees request paths starting
at ``/``.

Endpoints:

* ``GET  /healthz``                    unauthenticated liveness probe
* ``GET  /collections``                full state dump (one JSON blob)
* ``PUT  /collections/{key}``          replace one collection or singleton
* ``POST /audio-takes``                multipart upload of one recording
* ``GET  /audio-takes/{id}``           stream the raw audio bytes
* ``DELETE /audio-takes/{id}``         remove one take
* ``GET  /audio-takes``                list recent takes (metadata only)

Auth: every endpoint except ``/healthz`` requires
``Authorization: Bearer $KH_IELTS_API_TOKEN``.

CORS: allowed origins are taken from the comma-separated env var
``KH_IELTS_ALLOWED_ORIGINS``. Default is empty, i.e. same-origin only; set
it to e.g. ``https://ielts-sda-prep.vercel.app,http://localhost:5173`` in
production.

Everything is single-user. The hub serves one person and auth is the only
guard against drive-by writes.
"""

from __future__ import annotations

import io
import json
import os
import secrets
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from . import db


# ---- Config -------------------------------------------------------------


API_TOKEN = os.environ.get("KH_IELTS_API_TOKEN", "")
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("KH_IELTS_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]
MAX_AUDIO_BYTES = int(os.environ.get("KH_IELTS_MAX_AUDIO_BYTES", 25 * 1024 * 1024))

# Collection keys the client is allowed to sync. Any other key is rejected;
# this keeps the API from being used as a generic KV store.
ALLOWED_KEYS = {
    "sessions",
    "vocab",
    "writing_drafts",
    "sd_drafts",
    "band_mocks",
    "drill_checkoffs",
    "target_bands",
    "plan_start",
    "seeded_vocab",
}


# ---- App ----------------------------------------------------------------


app = FastAPI(
    title="IELTS × SD × PhD prep — sync API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "PUT", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        max_age=3600,
    )


@app.on_event("startup")
def _startup() -> None:
    db.init()


# ---- Auth ---------------------------------------------------------------


def require_bearer(request: Request) -> None:
    """Reject any request without a valid Bearer token.

    We use ``secrets.compare_digest`` to avoid trivial timing attacks even
    though the single-user threat model does not strictly require it.
    """
    if not API_TOKEN:
        # Fail-closed: an unset token means the operator forgot to
        # configure one. Refusing to serve is safer than opening the API.
        raise HTTPException(status_code=503, detail="API token not configured")
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = header[7:].strip()
    if not secrets.compare_digest(token, API_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid Bearer token")


# ---- Health -------------------------------------------------------------


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "ielts-sda-prep-api"}


# ---- Collections (whole-document sync) ----------------------------------


@app.get("/collections", dependencies=[Depends(require_bearer)])
def read_collections() -> JSONResponse:
    """Return the full state the client can rehydrate from.

    Values are returned as parsed JSON when the stored string parses, and
    as the raw string otherwise, so the client never has to guess.
    """
    out: dict[str, object] = {}
    for key, value in db.kv_all().items():
        if key not in ALLOWED_KEYS:
            # Future-proof: we may add internal keys later; don't leak them.
            continue
        try:
            out[key] = json.loads(value)
        except Exception:
            out[key] = value
    return JSONResponse(out)


class WriteBody(BaseModel):
    value: object = Field(..., description="JSON-serialisable value (collection or singleton).")


@app.put("/collections/{key}", dependencies=[Depends(require_bearer)])
def write_collection(key: str, body: WriteBody) -> dict[str, object]:
    if key not in ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"Unknown key: {key}")
    db.kv_set(key, json.dumps(body.value))
    return {"ok": True, "key": key}


@app.delete("/collections/{key}", dependencies=[Depends(require_bearer)])
def delete_collection(key: str) -> dict[str, object]:
    if key not in ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"Unknown key: {key}")
    db.kv_delete(key)
    return {"ok": True, "key": key}


# ---- Audio takes --------------------------------------------------------


@app.post("/audio-takes", dependencies=[Depends(require_bearer)])
async def upload_audio(
    file: UploadFile,
    session_id: Annotated[str | None, Form()] = None,
    kind: Annotated[str | None, Form()] = None,
    duration_sec: Annotated[int | None, Form()] = None,
) -> dict[str, object]:
    """Accept one audio blob (webm / mp4 / wav / ogg).

    Enforces a size cap of ``KH_IELTS_MAX_AUDIO_BYTES`` (default 25 MB) to
    protect SQLite from runaway uploads. Returns an id the client can use
    to fetch or delete the take.
    """
    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("audio/"):
        raise HTTPException(status_code=415, detail=f"Unsupported type: {content_type}")

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty upload")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Upload exceeds {MAX_AUDIO_BYTES} bytes",
        )

    take_id = uuid.uuid4().hex
    with db.connect() as con:
        con.execute(
            "INSERT INTO audio_takes (id, session_id, kind, duration_sec, "
            "content_type, size_bytes, created_at, blob) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                take_id,
                session_id,
                kind,
                duration_sec,
                content_type,
                len(data),
                db.now_ms(),
                data,
            ),
        )
    return {
        "ok": True,
        "id": take_id,
        "size_bytes": len(data),
        "content_type": content_type,
    }


@app.get("/audio-takes/{take_id}", dependencies=[Depends(require_bearer)])
def download_audio(take_id: str) -> StreamingResponse:
    with db.connect() as con:
        row = con.execute(
            "SELECT content_type, blob FROM audio_takes WHERE id = ?",
            (take_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    content_type, blob = row
    return StreamingResponse(io.BytesIO(blob), media_type=content_type)


@app.delete("/audio-takes/{take_id}", dependencies=[Depends(require_bearer)])
def delete_audio(take_id: str) -> dict[str, object]:
    with db.connect() as con:
        cur = con.execute("DELETE FROM audio_takes WHERE id = ?", (take_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True, "id": take_id}


@app.get("/audio-takes", dependencies=[Depends(require_bearer)])
def list_audio(limit: int = 50) -> list[dict[str, object]]:
    """Return the N most recent takes as metadata only (no blobs)."""
    limit = max(1, min(500, limit))
    with db.connect() as con:
        rows = con.execute(
            "SELECT id, session_id, kind, duration_sec, content_type, size_bytes, created_at "
            "FROM audio_takes ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "id": r[0],
            "session_id": r[1],
            "kind": r[2],
            "duration_sec": r[3],
            "content_type": r[4],
            "size_bytes": r[5],
            "created_at": r[6],
        }
        for r in rows
    ]


# ---- Content (public, read-only) ----------------------------------------


CONTENT_DIR = Path(os.environ.get(
    "KH_IELTS_CONTENT_DIR",
    str(Path(__file__).resolve().parents[2] / "content"),
))


def _load_manifest() -> list[dict]:
    mf = CONTENT_DIR / "manifest.json"
    try:
        return json.loads(mf.read_text(encoding="utf-8")).get("docs", [])
    except Exception:
        return []


@app.get("/content")
def list_content() -> JSONResponse:
    """Public: the manifest of bundled docs (grouped, no bodies)."""
    return JSONResponse({"docs": _load_manifest()})


@app.get("/content/{slug}")
def get_content(slug: str) -> JSONResponse:
    """Public: one doc's markdown + metadata."""
    docs = {d["slug"]: d for d in _load_manifest()}
    meta = docs.get(slug)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown doc")
    path = CONTENT_DIR / meta["file"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Doc file missing")
    return JSONResponse({**meta, "markdown": path.read_text(encoding="utf-8")})


# ---- Walkthroughs (public read, token-gated write) ----------------------
#
# Learning-aid walkthroughs (DSA, System Design, or anything else) that the
# UI can author and edit. Reads are public; writes require the Bearer token,
# so a public URL can't be vandalised. Stored as one JSON doc in `kv` under
# an internal key, which `read_collections` already filters out.


_WK_KEY = "__walkthroughs__"


def _wk_all() -> list[dict]:
    raw = db.kv_all().get(_WK_KEY)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []


def _wk_save(items: list[dict]) -> None:
    db.kv_set(_WK_KEY, json.dumps(items))


class WalkthroughBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    category: str = Field("Other", max_length=60)  # e.g. DSA | System Design | Other
    body: str = Field("", description="Markdown walkthrough content.")


@app.get("/walkthroughs")
def list_walkthroughs() -> JSONResponse:
    """Public: all learning-aid walkthroughs."""
    return JSONResponse({"walkthroughs": _wk_all()})


@app.get("/walkthroughs/{wid}")
def get_walkthrough(wid: str) -> JSONResponse:
    for w in _wk_all():
        if w.get("id") == wid:
            return JSONResponse(w)
    raise HTTPException(status_code=404, detail="Unknown walkthrough")


@app.post("/walkthroughs", dependencies=[Depends(require_bearer)])
def create_walkthrough(body: WalkthroughBody) -> dict[str, object]:
    items = _wk_all()
    now = db.now_ms()
    item = {
        "id": uuid.uuid4().hex,
        "title": body.title,
        "category": body.category,
        "body": body.body,
        "created_at": now,
        "updated_at": now,
    }
    items.append(item)
    _wk_save(items)
    return item


@app.put("/walkthroughs/{wid}", dependencies=[Depends(require_bearer)])
def update_walkthrough(wid: str, body: WalkthroughBody) -> dict[str, object]:
    items = _wk_all()
    for w in items:
        if w.get("id") == wid:
            w.update({
                "title": body.title,
                "category": body.category,
                "body": body.body,
                "updated_at": db.now_ms(),
            })
            _wk_save(items)
            return w
    raise HTTPException(status_code=404, detail="Unknown walkthrough")


@app.delete("/walkthroughs/{wid}", dependencies=[Depends(require_bearer)])
def delete_walkthrough(wid: str) -> dict[str, object]:
    items = _wk_all()
    kept = [w for w in items if w.get("id") != wid]
    if len(kept) == len(items):
        raise HTTPException(status_code=404, detail="Unknown walkthrough")
    _wk_save(kept)
    return {"ok": True, "id": wid}


# ---- Entry point --------------------------------------------------------


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8111"))
    uvicorn.run(
        "ielts_sda_prep_api.server:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
