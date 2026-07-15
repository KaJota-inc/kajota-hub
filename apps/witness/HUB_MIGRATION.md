# Deployment moved to the KaJota Hub

This service is now served from the consolidated **kajota-hub** instance
(one Render box hosting several formerly-standalone services behind a
path-routing reverse proxy).

| | URL |
|---|---|
| **Current (hub)** | https://kajota-hub.onrender.com/witness  · `/ui` · `/verify` · `/health` |
| Previous (standalone, may be retired) | https://kajota-witness.onrender.com |

Doc/manifest references now point at the hub URL; the old standalone URL is
kept here for reference and any external links that still use it.
