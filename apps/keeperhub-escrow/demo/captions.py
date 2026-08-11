"""Render SRT cues to transparent PNGs and emit the ffmpeg overlay chain.

This ffmpeg has no libass, so the `subtitles` filter does not exist — the
force_style parse errors were the symptom, not the cause. Captions get
drawn with PIL instead and composited as timed overlays.
"""
import json, os, re, subprocess, sys

from PIL import Image, ImageDraw, ImageFont

SRT = "v6-fixed.srt"
OUTDIR = "caps"
W, H = 1920, 1080
MARGIN_BOTTOM = 74
FONTSIZE = 34
PAD_X, PAD_Y = 26, 14

os.makedirs(OUTDIR, exist_ok=True)

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/SFNS.ttf",
    "/Library/Fonts/Arial.ttf",
]
font = None
for p in FONT_CANDIDATES:
    if os.path.exists(p):
        try:
            font = ImageFont.truetype(p, FONTSIZE)
            print("font:", p)
            break
        except Exception:
            continue
if font is None:
    sys.exit("no usable font found")


def secs(ts):
    h, m, rest = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest.replace(",", "."))


cues = []
for blk in open(SRT).read().strip().split("\n\n"):
    lines = blk.strip().split("\n")
    if len(lines) < 3:
        continue
    m = re.match(r"(\S+) --> (\S+)", lines[1])
    cues.append((secs(m.group(1)), secs(m.group(2)), " ".join(lines[2:]).strip()))

print("cues:", len(cues))

for i, (a, b, text) in enumerate(cues):
    tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    box = d.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]

    bw, bh = tw + PAD_X * 2, th + PAD_Y * 2
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    dd = ImageDraw.Draw(img)
    # Semi-opaque plate: the console is dark but the hero is not uniformly so,
    # and white-on-transparent goes unreadable over the bright green headline.
    dd.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=8, fill=(0, 0, 0, 190))
    dd.text((PAD_X - box[0], PAD_Y - box[1]), text, font=font, fill=(255, 255, 255, 255))
    img.save(f"{OUTDIR}/c{i:03d}.png")

with open("caps.json", "w") as f:
    json.dump([{"i": i, "a": a, "b": b} for i, (a, b, _) in enumerate(cues)], f)

print("rendered", len(cues), "caption plates →", OUTDIR)
