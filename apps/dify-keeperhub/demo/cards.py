"""Render the title, guard and close cards, plus caption plates.

Silent, caption-driven cut: there is no voice track, so every claim has to be
legible on screen. The guard card typesets the REAL recorded tool output
rather than a mock-up — it is a transcript, and is labelled as one.
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BG = (5, 5, 7)
FG = (238, 238, 240)
DIM = (150, 152, 158)
GREEN = (45, 255, 125)
AMBER = (255, 190, 70)
RED = (255, 105, 105)

def font(path_candidates, size):
    for p in path_candidates:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

SANS = ["/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc"]
MONO = ["/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/System/Library/Fonts/Courier.ttc"]

os.makedirs("cards", exist_ok=True)

def card(name, lines):
    """lines: list of (text, font, fill, gap_after)"""
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    total = 0
    for t, f, _c, gap in lines:
        total += (d.textbbox((0,0), t or "x", font=f)[3] - d.textbbox((0,0), t or "x", font=f)[1]) + gap
    y = (H - total) // 2
    for t, f, c, gap in lines:
        bb = d.textbbox((0,0), t or "x", font=f)
        h = bb[3] - bb[1]
        if t:
            d.text((150, y - bb[1]), t, font=f, fill=c)
        y += h + gap
    im.save(f"cards/{name}.png")
    print("  ✓", name)

h1 = font(SANS, 74); h2 = font(SANS, 40); body = font(SANS, 34)
mono = font(MONO, 27); mono_s = font(MONO, 24); small = font(SANS, 26)

# ---- title -----------------------------------------------------------
card("c1-title", [
    ("KeeperHub for Dify", h1, FG, 26),
    ("", body, FG, 8),
    ("Dify agents can decide anything.", h2, DIM, 10),
    ("They cannot move value onchain reliably.", h2, DIM, 34),
    ("This plugin lets them — and shows what a", body, FG, 6),
    ("transaction would do before anything is signed.", body, FG, 0),
])

# ---- the guard, as a transcript --------------------------------------
im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
d.text((150, 96), "The guard is the default, not an option", font=h2, fill=FG)
d.text((150, 152), "recorded output of execute_call, same arguments both times", font=small, fill=DIM)
y = 232
d.text((150, y), "1  no acknowledgement", font=mono, fill=AMBER); y += 46
for ln, col in [("executed: false", RED),
                ("simulated_instead: true", GREEN),
                ('"Refused to execute: this call moves value', DIM),
                (' onchain and `acknowledge_moves_value`', DIM),
                (' was not true. Simulated it instead."', DIM)]:
    d.text((196, y), ln, font=mono_s, fill=col); y += 38
y += 42
d.text((150, y), "2  acknowledge_moves_value: true", font=mono, fill=GREEN); y += 46
for ln, col in [("executed: true", GREEN),
                ("tx 0x4c316e38…eb0335", FG)]:
    d.text((196, y), ln, font=mono_s, fill=col); y += 38
y += 34
d.text((150, y), "An agent that omits the flag gets a dry run. Nothing", font=body, fill=DIM); y += 42
d.text((150, y), "irreversible happens by omission.", font=body, fill=DIM)
im.save("cards/c6-guard.png"); print("  ✓ c6-guard")

# ---- close -----------------------------------------------------------
card("c8-close", [
    ("Dify workflow  >  tool node  >  plugin", h2, FG, 12),
    (">  keeperhub-mcp  >  KeeperHub  >  Sepolia", h2, FG, 40),
    ("Built on KeeperHub's own published MCP kernel.", body, DIM, 8),
    ("38 tests. Testnet by default, on purpose.", body, DIM, 34),
    ("github.com/KaJota-inc/kajota-hub", small, GREEN, 0),
])

# ---- caption plates for the screen shots -----------------------------
CAPS = {
  "cap-canvas":   "A Dify workflow with one KeeperHub node — it cannot sign or broadcast",
  "cap-tracing":  "Run it: the tool is invoked, 1.592s",
  "cap-result":   "signed: false · broadcast: false — nothing touched the chain",
  "cap-detail":   "SUCCESS · 1.777s · 3 steps",
  "cap-explorer": "With the acknowledgement: a real transaction, block 11690913",
}
cf = font(SANS, 36)
for name, text in CAPS.items():
    tmp = Image.new("RGBA", (W, H), (0,0,0,0)); dd = ImageDraw.Draw(tmp)
    bb = dd.textbbox((0,0), text, font=cf)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    pad_x, pad_y = 30, 18
    plate = Image.new("RGBA", (tw+pad_x*2, th+pad_y*2), (0,0,0,205))
    pd = ImageDraw.Draw(plate)
    pd.rounded_rectangle([0,0,plate.size[0]-1,plate.size[1]-1], radius=10, fill=(0,0,0,205))
    pd.text((pad_x-bb[0], pad_y-bb[1]), text, font=cf, fill=(255,255,255,255))
    plate.save(f"cards/{name}.png")
    print("  ✓", name, plate.size)
