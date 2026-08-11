import json, os, subprocess
caps = json.load(open("caps.json"))
VO = os.path.expanduser("~/Downloads/vo-v2-tight.m4a")
OUT = os.path.expanduser("~/Downloads/kajota-coach-demo-v6.mp4")

args = ["ffmpeg", "-y", "-v", "error", "-i", "work2/silent.mp4", "-i", VO]
for c in caps:
    args += ["-i", f"caps/c{c['i']:03d}.png"]

chain, cur = [], "0:v"
for n, c in enumerate(caps):
    inp = n + 2                      # 0 = video, 1 = audio, captions start at 2
    lbl = f"v{n}"
    chain.append(
        f"[{cur}][{inp}:v]overlay=x=(W-w)/2:y=H-h-74:"
        f"enable='between(t,{c['a']:.3f},{c['b']:.3f})'[{lbl}]"
    )
    cur = lbl
fc = ";".join(chain)

args += ["-filter_complex", fc, "-map", f"[{cur}]", "-map", "1:a:0",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
print("overlays:", len(caps))
r = subprocess.run(args)
raise SystemExit(r.returncode)
