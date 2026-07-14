"""Generate square logo + 16:9 thumbnail for the 0G Arena project page."""
from PIL import Image, ImageDraw, ImageFont

BG = (28, 25, 23)
AMBER = (251, 191, 36)
WHITE = (250, 250, 249)
GREY = (120, 113, 108)
EMERALD = (52, 211, 153)
INDIGO = (129, 140, 248)

SFNS = "/System/Library/Fonts/SFNS.ttf"


def make_logo(path: str, size: int = 512) -> None:
    """Square logo — the W mark on amber on stone-900 background."""
    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)
    # Amber W mark, centered
    box = int(size * 0.5)
    bx = (size - box) // 2
    by = (size - box) // 2
    d.rectangle([bx, by, bx + box, by + box], fill=AMBER)
    f = ImageFont.truetype(SFNS, int(box * 0.65))
    bbox = d.textbbox((0, 0), "W", font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((bx + box / 2 - tw / 2 - bbox[0], by + box / 2 - th / 2 - bbox[1]),
           "W", fill=BG, font=f)
    img.save(path)


def make_thumbnail(path: str) -> None:
    """16:9 cover image — for hackathon cards + voting gallery."""
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # Top accent bar
    d.rectangle([0, 0, W, 8], fill=AMBER)
    # W mark on left side
    box = 110
    bx = 90
    by = (H - box) // 2 - 20
    d.rectangle([bx, by, bx + box, by + box], fill=AMBER)
    f_w = ImageFont.truetype(SFNS, 80)
    bbox = d.textbbox((0, 0), "W", font=f_w)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((bx + box / 2 - tw / 2 - bbox[0], by + box / 2 - th / 2 - bbox[1]),
           "W", fill=BG, font=f_w)
    # Headline + tagline to the right
    text_x = bx + box + 40
    f_h = ImageFont.truetype(SFNS, 64)
    d.text((text_x, H // 2 - 90), "KAJOTA WITNESS", fill=AMBER, font=f_h)
    f_t = ImageFont.truetype(SFNS, 28)
    d.text((text_x + 2, H // 2 - 10),
           "encrypted seller memory + AI jury", fill=WHITE, font=f_t)
    d.text((text_x + 2, H // 2 + 26),
           "for African micro-commerce, on 0G Galileo", fill=WHITE, font=f_t)
    # 3 colored pills (one per 0G surface) at bottom
    pill_y = H - 110
    pills = [("Storage", EMERALD), ("Chain", AMBER), ("Anchor", INDIGO)]
    pill_x = text_x
    f_p = ImageFont.truetype(SFNS, 22)
    for label, color in pills:
        bbox = d.textbbox((0, 0), label, font=f_p)
        pw = bbox[2] - bbox[0] + 32
        d.rectangle([pill_x, pill_y, pill_x + pw, pill_y + 38],
                    fill=BG, outline=color, width=2)
        d.text((pill_x + 16, pill_y + 4), label, fill=color, font=f_p)
        pill_x += pw + 16
    # Bottom-right event tag
    f_e = ImageFont.truetype(SFNS, 20)
    evt = "0G Zero Cup 2026"
    bbox = d.textbbox((0, 0), evt, font=f_e)
    d.text((W - (bbox[2] - bbox[0]) - 40, H - 50),
           evt, fill=GREY, font=f_e)
    img.save(path)


if __name__ == "__main__":
    import sys
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    make_logo(f"{out_dir}/logo.png")
    make_thumbnail(f"{out_dir}/thumbnail.png")
    print(f"wrote logo.png + thumbnail.png to {out_dir}")
