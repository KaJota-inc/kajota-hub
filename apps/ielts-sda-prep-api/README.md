# ielts-sda-prep-api

Single-user sync backend for the IELTS × System Design × PhD prep React app.
Mounted at `https://kajota-hub.onrender.com/ielts-sda-prep-api/*` on port
`8111`. Pairs with the Vercel-hosted client at (TBD).

## Why it exists

The client was previously `localStorage`-only. The PhD prep campaign spans
49 days (14 Oct → 1 Dec 2026) and runs across laptop + phone + tablet; a
central sync layer lets any browser pick up the exact progress state the
others left. Audio recordings (Speaking takes) are included; everything
else is small JSON documents.

## Shape

| Table / key | What |
|---|---|
| `kv` table | JSON-document store, one row per collection or singleton. Keys allowed: `sessions`, `vocab`, `writing_drafts`, `sd_drafts`, `band_mocks`, `drill_checkoffs`, `target_bands`, `plan_start`, `seeded_vocab`. |
| `audio_takes` table | One row per uploaded recording. Blob + `(session_id, kind, duration_sec, content_type, size_bytes, created_at)`. |

## Endpoints

Every endpoint except `/healthz` requires
`Authorization: Bearer $KH_IELTS_API_TOKEN`.

| Method | Path | Description |
|---|---|---|
| GET | `/healthz` | Liveness probe. Returns `{"status": "ok"}`. |
| GET | `/collections` | Full state dump — all `kv` rows parsed to JSON. |
| PUT | `/collections/{key}` | Replace one collection or singleton. Body: `{"value": …}`. |
| DELETE | `/collections/{key}` | Remove one key. |
| POST | `/audio-takes` | Multipart: `file` + `session_id` + `kind` + `duration_sec`. Returns `{id}`. 25 MiB cap. |
| GET | `/audio-takes/{id}` | Stream the raw audio bytes with the stored MIME type. |
| DELETE | `/audio-takes/{id}` | Remove one take. |
| GET | `/audio-takes` | Metadata list (no blobs) of the N most recent takes. |

## Required Render env

| Var | Purpose |
|---|---|
| `KH_IELTS_API_TOKEN` | **Required.** Shared secret between this backend and the React client's `VITE_API_TOKEN`. If unset, every authed endpoint 503s (fail-closed). |
| `KH_IELTS_ALLOWED_ORIGINS` | Comma-separated allow-list for CORS. Example: `https://ielts-sda-prep.vercel.app,http://localhost:5173`. Empty = same-origin only. |
| `KH_IELTS_DB_PATH` | SQLite file path. Must sit on a persistent Render disk mount in production, e.g. `/srv/data/ielts-sda-prep-api.sqlite3`. |
| `KH_IELTS_MAX_AUDIO_BYTES` | Per-upload cap in bytes. Default `26214400` (25 MiB). |

## Local dev

```bash
cd apps/ielts-sda-prep-api
python -m venv .venv && source .venv/bin/activate
pip install -e .
export KH_IELTS_API_TOKEN="dev-token"
export KH_IELTS_ALLOWED_ORIGINS="http://localhost:5173"
export KH_IELTS_DB_PATH="./dev.sqlite3"
PORT=8111 python -m ielts_sda_prep_api.server
```

Then from the React app's `.env.local`:

```
VITE_API_BASE=http://localhost:8111
VITE_API_TOKEN=dev-token
```

## Operational notes

- **Fail-closed on missing token.** The absence of `KH_IELTS_API_TOKEN`
  returns `503` to every authed call. This is deliberate: an open sync
  endpoint on a public domain is a worse failure mode than an outage.
- **One-user design.** No `user_id` column anywhere. Rotating the token
  rotates access for every browser.
- **Audio durability.** Blobs live in SQLite. Backups are a plain file
  copy of the `.sqlite3` file. 25 MiB per take × a few takes per day ×
  49 days = several hundred MB over the campaign; comfortably within
  Render's persistent-disk tiers.
- **No queueing / background work.** Every request is handled inline.
  This is appropriate for the traffic profile (one user, a few writes
  per minute at most).
