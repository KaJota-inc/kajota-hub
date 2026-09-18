# Submitted — KeeperHub Agent Economy

Both BUIDLs went in on 2026-09-18, ahead of the 11:00 Lagos / 12:00 CEST
deadline. Both read **Under Review**.

| | BUIDL | track / bounty |
|---|---|---|
| Main track | [#48913 KeeperHub for Dify](https://dorahacks.io/buidl/48913) | Best Integration into a Live Project |
| Bounty | [#48914 validate_workflow: catch the signer-routing key that does nothing](https://dorahacks.io/buidl/48914) | Best KeeperHub Feature ($1,000, two winners) |

Winners announced **Sep 24/25**. Up to ten finalists present live to judges
on a call, invited by email beforehand — see `PITCH.md` from the previous
event for the shape of that, but note the rules differ: this time you
present the working build, not slides.

## Verified at submission time

- source `github.com/KaJota-inc/kajota-hub/tree/main/apps/dify-keeperhub` — 200, public
- video `youtu.be/kq3OB3RNJiE` — 200, public, 78s, hd1080 available
- tx `0x4c316e38…eb0335` — blockscout: success, block 11690913, `execute`
- PR [#2538](https://github.com/KeeperHub/keeperhub/pull/2538) and issue
  [#2431](https://github.com/KeeperHub/keeperhub/issues/2431) — both 200
- Dify 156,182 stars, pushed the same day, so "live project with users" holds

## Form facts worth keeping

The announcement page understates what the form demands:

- **Logo required** (PNG/JPEG, 480x480). An SVG is rejected.
  `apps/dify-keeperhub/_assets/buidl-logo-480.png`.
- **Social links required**, at least one.
- **Telegram required**, plus one backup contact. The step states this data
  is visible only to DoraHacks staff, which is why it was filled at all;
  WhatsApp and WeChat were left blank.
- **960-character cap** on each of the two "Additional information"
  answers, undocumented and only enforced on submit. The long-form content
  lives in the description field, which has no such cap.
- **No transaction field exists**, so the tx link leads the description.
- The description editor has a raw-Markdown mode behind a "Switch to
  editor" toggle. Pasting Markdown into the rich-text mode leaves it
  literal *and* mangles non-ASCII (an em dash arrived as `,Äì`), so the
  copy was flattened to ASCII first.
- The Track dropdown offers only the main track; a bounty entry is
  distinguished by applying through the bounty's own Apply flow, not by a
  track value. A BUIDL already applied to a bounty appears greyed out and
  unselectable in that picker — which is how to confirm it attached.

## Left to do

- Correct the Discord handle if `boriadura` is wrong — BUIDLs stay editable
  until judging.
- Rotate the KeeperHub API key pasted in chat, and unset `KH_WATCHER_LIVE`
  on kajota-hub (still armed from the previous hackathon).
