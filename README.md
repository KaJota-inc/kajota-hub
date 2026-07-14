# kajota-hub

Consolidates six Render free-tier services into **one paid instance** to stop
blowing the 750 free-hours/month budget. A [Caddy](Caddyfile) reverse proxy
listens on `$PORT` and routes by path prefix to six app processes managed by
[supervisord](supervisord.conf). Each Python app gets its **own venv** so their
dependency pins never collide.

| Route | App | Repo / branch | Runtime | Internal port |
|---|---|---|---|---|
| `/coach-okx` | coach-okx | kajota-coach-okx `agent` @ hackathon/okx-asp | Python/FastAPI + Node | 8101 |
| `/mesh-okx` | mesh-okx | kajota-coach-okx `skill` @ hackathon/okx-asp | Python/FastAPI | 8102 |
| `/concierge` | concierge | kajota-coach `agent` @ hackathon/rapid-agent | Python/FastAPI + Node | 8103 |
| `/slack` | slack | kajota-coach-slack `agent` @ hackathon/slack | Python/FastAPI + Node | 8104 |
| `/mesh-skill` | mesh-skill | kajota-coach `skill` @ hackathon/rapid-agent | Python/FastAPI | 8105 |
| `/witness` | witness | kajota-witness @ main | Node/Fastify (tsx) | 8106 |

**`spirit-of-glory-api` is deliberately NOT here** — it's a JVM/Spring-Boot
**prod** backend that idles ~350–450 MB (nearly a whole 512 MB box) and
shouldn't be coupled to hackathon demos. Keep it on its own Starter with
`JAVA_TOOL_OPTIONS=-Xmx350m`.

## Build & deploy

```bash
# 1. Vendor app source from the sibling repos into apps/ (self-contained build)
./scripts/vendor.sh

# 2. Commit, push to a GitHub repo, connect it to Render, point at render.yaml
# 3. Set the sync:false secrets + Secret Files in the Render dashboard
```

Local smoke test:

```bash
docker build -t kajota-hub .
docker run --rm -p 10000:10000 --env-file .env kajota-hub
curl localhost:10000/healthz            # -> ok
curl localhost:10000/witness/health     # -> witness app
```

## Env vars are namespaced per app

Because `coach-okx`, `concierge`, and `slack` are the **same codebase** (they all
read `MONGODB_URI`, `GEMINI_MODEL`, `GCP_*`), and `mesh-okx`/`mesh-skill` both
read `MESH_*`, config is namespaced in Render and the prefix is stripped at
launch by `scripts/run/<app>.sh`:

| Prefix | App | Example |
|---|---|---|
| `COKX_` | coach-okx | `COKX_MONGODB_URI` → `MONGODB_URI` |
| `CONC_` | concierge | `CONC_MONGODB_URI` → `MONGODB_URI` |
| `SLK_` | slack | `SLK_SLACK_BOT_TOKEN` → `SLACK_BOT_TOKEN` |
| `MOKX_` | mesh-okx | `MOKX_MESH_CHAIN_ID` → `MESH_CHAIN_ID` |
| `MSKL_` | mesh-skill | `MSKL_MESH_RPC_URL` → `MESH_RPC_URL` |
| _(none)_ | witness | `ZG_RPC_URL`, `GROQ_API_KEY`, `WITNESS_*` |

See [render.yaml](render.yaml) for the full list. GCP service-account JSON
goes in as a **Secret File** (one per agent app), with the matching
`*_GOOGLE_APPLICATION_CREDENTIALS` var pointing at its mount path.

## Known limits (read before cutover)

1. **`coach-okx` is a live OKX.AI Genesis ASP endpoint, under review Jul 13–14,
   deadline Jul 17.** Its registered URL *is* the service URL. Moving it to
   `…/coach-okx` means re-registering with OKX. **Do NOT cut coach-okx/mesh-okx
   over until after Jul 17** — for the deadline, just upgrade those two in place.
   The hub is ready for them whenever you're clear of the review window.
2. **Path prefixes are stripped** (`handle_path`), so apps work unmodified. Any
   app that emits an **absolute self-URL** — notably coach-okx's x402 pay URL —
   must honor its mount point. `X-Forwarded-Prefix` is forwarded for this;
   wire FastAPI `root_path` from it when you enable x402 behind the hub.
3. **One health check for the whole box.** Render polls `/healthz` at the Caddy
   layer, so a single dead backend won't flip Render's status. Check
   `/<app>/health(z)` per app, or watch the `[program:<name>]` logs.
4. **Shared blast radius / build coupling** — one image owns six apps; a bad
   deploy affects all. That's the tradeoff for $25/mo instead of ~$49.
