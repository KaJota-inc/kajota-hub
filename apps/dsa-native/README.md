# dsa-native

DSA + AI-native interview prep daily driver. Static SPA + Express `/api/sync` route backed by MongoDB.

Mounted at **`/dsa-native/*`** via Caddy → `127.0.0.1:8112` → this process.

## Layout

```
apps/dsa-native/
├── package.json       # express + mongodb only
├── server.js          # Express app · static + /api/sync + /healthz
└── public/
    ├── index.html     # SPA (self-contained, no bundler)
    └── content.json   # 40 workflow files baked at build time
```

## Env

| Var | Required | Note |
|---|---|---|
| `PORT` | yes | Set by `scripts/run/dsa-native.sh` to `8112` |
| `MONGODB_URI` | yes | Mapped from `DSAN_MONGODB_URI` in `render.yaml`. Unset → `/api/sync` returns 503. |
| `MONGODB_DB` | no | Defaults to `dsa_native`. |

## Routes

- `GET  /`                     → SPA (serves `public/index.html`)
- `GET  /content.json`         → baked workflow library (CDN-cached 5min / 1h)
- `GET  /api/sync?token=...`   → read state (204 if none, 200 with `{state,fetchedAt}` otherwise)
- `POST /api/sync` body `{token,state}` → upsert state (returns `{ok,bytes,savedAt}`)
- `DELETE /api/sync?token=...` → remove state
- `GET  /healthz`              → `{status:"ok",configured,uptime,db}`

Max state blob: 256 KB (fails with 413 otherwise).

## Local dev

```bash
cd apps/dsa-native
npm install
MONGODB_URI='mongodb+srv://...' PORT=8112 node server.js
# → http://127.0.0.1:8112
```

## Refresh baked content

The SPA + content.json are copied from `~/Documents/dsa-native-web/public/` whenever the upstream prep folders change:

```bash
cd ~/Documents/dsa-native-web && npm run build
cp public/index.html public/content.json ~/Documents/kajota-hub/apps/dsa-native/public/
cd ~/Documents/kajota-hub
git add apps/dsa-native/public && git commit -m "chore(dsa-native): refresh library"
git push   # Render redeploys the hub
```

## History

Migrated from Vercel on 2026-10-14. The Hobby-plan commit-email check blocked every redeploy past the first; moving to kajota-hub puts the app on the same shared Mongo cluster, no author gate.
