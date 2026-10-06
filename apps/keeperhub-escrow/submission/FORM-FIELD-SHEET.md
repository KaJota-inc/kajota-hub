# DoraHacks form — exact values, field by field

Walked the live form on 2026-09-18 00:0x Lagos. Five steps:
**Profile → Details → Team → Contact → Submission.** Every field below is
one the form actually renders; three things the brief does not mention are
flagged.

**Deadline: Fri 18 Sep 11:00 Lagos = 12:00 CEST.**

---

## Things the announcement page does not tell you

1. **A logo is required** — `*` on "BUIDL logo", JPEG or PNG under 2 MB,
   480 x 480 recommended. Neither draft had one; we only had a 326-byte
   SVG, which the form does not accept. Now:
   `apps/dify-keeperhub/_assets/buidl-logo-480.png` (PNG, 480x480, 8.4 KB).
2. **There is no transaction field.** The brief demands a transaction link
   and says incomplete submissions cannot be judged, but the form has
   nowhere to put one — so it has to go in the description body, where a
   judge will actually look for it. Both descriptions lead with it.
3. **The contact step invites Telegram, WhatsApp and WeChat.**
   Leave all three blank — see the privacy note at the bottom. The brief
   only asks for "email plus an X or Discord handle".

---

## BUIDL 1 — main track

| step | field | value |
|---|---|---|
| Profile | BUIDL name * | `KeeperHub for Dify` |
| Profile | BUIDL logo * | `apps/dify-keeperhub/_assets/buidl-logo-480.png` |
| Profile | Vision * | Dify agents can decide anything. They cannot move value onchain reliably. This plugin lets them - and shows what a transaction would do before anything is signed. |
| Profile | Category * | **Crypto / Web3** (AI / Robotics is the second-best fit; the form takes one) |
| Profile | GitHub * | `https://github.com/KaJota-inc/kajota-hub/tree/main/apps/dify-keeperhub` |
| Profile | Project website | `https://marketplace.dify.ai` — leave blank instead; we have no landing page and pointing at Dify's own marketplace would misrepresent an unlisted plugin |
| Profile | Demo video * | `https://youtu.be/kq3OB3RNJiE` |
| Profile | Social link | `https://x.com/Oluwabori6` |
| Details | Description | body of `BUIDL-1-main-track.md` — carries the tx link and all five brief questions |
| Team | member search | solo; skip |
| Contact | Telegram / WhatsApp / WeChat | **blank** |
| Contact | Discord | `boriadura` only if a Discord handle is wanted; otherwise rely on email + X |
| Submission | track | main track — **not** the bounty |

## BUIDL 2 — bounty (separate BUIDL, one track each)

| step | field | value |
|---|---|---|
| Profile | BUIDL name * | `validate_workflow: catch the signer-routing key that does nothing` |
| Profile | BUIDL logo * | same PNG |
| Profile | Vision * | An agent composing a KeeperHub workflow reaches for integrationId to pick a wallet. No web3 step reads it. This makes the validator say so - and names the field that does work, which the MCP surface never mentioned. |
| Profile | Category * | **Crypto / Web3** |
| Profile | GitHub * | `https://github.com/KeeperHub/keeperhub/pull/2538` |
| Profile | Demo video * | `https://youtu.be/kq3OB3RNJiE` (required field; a validator rule renders nothing, so this is the main-track cut) |
| Details | Description | body of `BUIDL-2-bounty.md` |
| Submission | track | **bounty — Best KeeperHub Feature** |

---

## Privacy note — load-bearing

The contact step has dedicated Telegram and WhatsApp inputs. The owner's
personal Telegram and WhatsApp must not be republished on a public
submission page. Email + X + GitHub are the public channels:

`oluwaboriife@gmail.com` · X `@Oluwabori6` · GitHub `@KaJota-inc`

## Both descriptions must open with the three mandatory artefacts

The brief: "a source code link, a short demo video showing the integration
working, and a link to a transaction executed through KeeperHub.
Incomplete submissions cannot be judged." All three verified live:

- source `https://github.com/KaJota-inc/kajota-hub/tree/main/apps/dify-keeperhub` — 200, public
- video `https://youtu.be/kq3OB3RNJiE` — 200, public, 78s, hd1080 available
- tx `https://eth-sepolia.blockscout.com/tx/0x4c316e389ad51ca7e8bf88e1d0f656215164b8ec1a11f8d21c00239ae7eb0335` — success, block 11690913
