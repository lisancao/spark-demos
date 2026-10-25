#!/usr/bin/env python3
"""Film a demo from a VHS tape.

  film.py render <tape> [--format landscape|vertical] [--theme spark|nullstone] [--only ID,...]
      VHS master: one clip per beat in renders/<format>/, joined into
      renders/<name>-<format>.mp4, with a cue sheet and a voiceover guide (SRT).
  film.py real <tape>
      The same tape typed into Lisa's own kitty (her config, prompt, aliases) on a
      hidden X display; renders/<name>-real.mp4 with hidden sections cut out.
  film.py ide <film folder> [--trim SECONDS]
      Finish an IDE take (film/kit/ide): renders/take-raw.mp4 and take.marks become
      a 1080p landscape cut and a vertical cut that zooms into each beat's `focus`
      box from storyboard.md, both with a cue sheet and a voiceover guide.
  film.py zoom <video> [--format landscape|vertical] [--space WxH]
      Dynamic zoom over a finished cut, from the storyboard's `zoom` column and the
      cut's cue sheet: <stem>-zoom.mp4, plus <stem>.openscreen, the same zooms as an
      OpenScreen project to adjust and re-export by hand.
  film.py sheet <video> [--every SECONDS]
      Contact sheet with timestamps, for reviewing a take frame by frame.

A tape is ordinary VHS with two conventions:
  - Everything before the first `# beat:` line is setup. It runs hidden at the start
    of every clip (wrap it in Hide/Show), so each beat stands alone.
  - `# beat: <id> | <title>` starts a beat. The beat ids match the rows of the
    storyboard.md next to the tape, whose VO column becomes the voiceover guide.
Size, font and theme come from formats/ and themes/, not from the tape. The shell
gets FILM_KIT, FILM_DEMO (the demo folder), FILM_THEME and FILM_FORMAT; the real pass also sets
FILM_REAL=1 so the setup can keep Lisa's own prompt.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KIT = Path(__file__).resolve().parent
BEAT = re.compile(r"^#\s*beat:\s*([\w.-]+)\s*(?:\|\s*(.*))?$")


def parse_tape(path):
    """Split a tape into its Set lines, its setup, and its beats."""
    sets, setup, beats = [], [], []
    for line in path.read_text().splitlines():
        m = BEAT.match(line.strip())
        if m:
            beats.append({"id": m[1], "title": (m[2] or m[1]).strip(), "lines": []})
        elif line.startswith("Set ") and not beats:
            sets.append(line)
        elif line.startswith("Output "):
            continue  # outputs are the runner's job
        elif beats:
            beats[-1]["lines"].append(line)
        else:
            setup.append(line)
    if not beats:
        sys.exit(f"{path}: no '# beat:' lines")
    return sets, setup, beats


def storyboard_vo(tape, column="vo"):
    """Beat id -> cell, from the storyboard.md tables next to the tape that have the column."""
    sb = (tape if tape.is_dir() else tape.parent) / "storyboard.md"
    if not sb.exists():
        return {}
    vo, cols = {}, None
    for line in sb.read_text().splitlines():
        if not line.startswith("|"):
            cols = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cols is None:
            cols = [c.lower() for c in cells]
            continue
        if set(line) <= set("|-: "):
            continue
        if column in cols:
            vo[cells[0].strip("`")] = cells[cols.index(column)]
    return vo


def demo_dir(tape, override):
    return Path(override).resolve() if override else tape.resolve().parent.parent


def film_env(tape, args, real=False):
    env = dict(os.environ, FILM_KIT=str(KIT), FILM_DEMO=str(demo_dir(tape, args.demo)),
               FILM_THEME=getattr(args, "theme", "spark"), FILM_FORMAT=getattr(args, "format", "landscape"))
    if real:
        env["FILM_REAL"] = "1"
    return env


def duration(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(video)], capture_output=True, text=True, check=True)
    return float(out.stdout)


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_cues(stem, cues, vo):
    """cues: [(id, title, start, end)] -> stem.cues.tsv and stem.vo.srt"""
    with open(f"{stem}.cues.tsv", "w") as f:
        f.write("beat\tstart\tend\tseconds\ttitle\tvo\n")
        for bid, title, a, b in cues:
            f.write(f"{bid}\t{a:.2f}\t{b:.2f}\t{b - a:.2f}\t{title}\t{vo.get(bid, '')}\n")
    with open(f"{stem}.vo.srt", "w") as f:
        for i, (bid, title, a, b) in enumerate(cues, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{vo.get(bid) or '[' + title + ']'}\n\n")
    width = max(len(c[0]) for c in cues)
    for bid, title, a, b in cues:
        words = len(vo.get(bid, "").split())
        need = words / 2.5  # a calm read is about 150 words a minute
        flag = f"  VO needs ~{need:.0f}s" if need > b - a else ""
        print(f"  {bid:<{width}}  {a:6.1f}  {b - a:5.1f}s{flag}")


# ---------------------------------------------------------------- render (VHS)

def render(args):
    tape = Path(args.tape).resolve()
    sets, setup, beats = parse_tape(tape)
    theme = json.loads((KIT / "themes" / f"{args.theme}.json").read_text())
    out = tape.parent / "renders" / args.format
    out.mkdir(parents=True, exist_ok=True)
    head = ["Set Shell zsh", 'Set FontFamily "JetBrainsMono Nerd Font Mono"', "Set Framerate 30",
            "Set CursorBlink false", "Set WaitTimeout 90s",
            *(KIT / "formats" / f"{args.format}.tape").read_text().splitlines(),
            f"Set Theme {json.dumps(theme)}", *sets]
    only = set(args.only.split(",")) if args.only else None
    env = film_env(tape, args)
    clips = []
    for i, beat in enumerate(beats, 1):
        clip = out / f"{i:02d}-{beat['id']}.mp4"
        clips.append((beat, clip))
        if only and beat["id"] not in only:
            if not clip.exists():
                sys.exit(f"{clip} missing; render it first")
            continue
        body = "\n".join([*head, f'Output "{clip}"', *setup, *beat["lines"]]) + "\n"
        with tempfile.NamedTemporaryFile("w", suffix=".tape", dir=out, delete=False) as f:
            f.write(body)
        print(f"[{beat['id']}] rendering", flush=True)
        t0 = time.time()
        r = subprocess.run(["vhs", "-q", f.name], env=env, cwd=out)
        os.unlink(f.name)
        if r.returncode:
            sys.exit(f"vhs failed on beat {beat['id']}")
        print(f"[{beat['id']}] {duration(clip):.1f}s ({time.time() - t0:.0f}s to render)")
    stem = tape.parent / "renders" / f"{tape.stem}-{args.format}"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.writelines(f"file '{c}'\n" for _, c in clips)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f.name,
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", f"{stem}.mp4"], check=True)
    os.unlink(f.name)
    cues, t = [], 0.0
    for beat, clip in clips:
        d = duration(clip)
        cues.append((beat["id"], beat["title"], t, t + d))
        t += d
    print(f"{stem}.mp4  {t:.1f}s")
    write_cues(stem, cues, storyboard_vo(tape))


# ------------------------------------------------------- real pass (her kitty)

KEYS = {"Enter": "enter", "Escape": "escape", "Tab": "tab", "Space": "space", "Backspace": "backspace",
        "Up": "up", "Down": "down", "Left": "left", "Right": "right", "PageUp": "page_up",
        "PageDown": "page_down", "Home": "home", "End": "end", "Delete": "delete"}


def seconds(tok):
    tok = tok.strip()
    if tok.endswith("ms"):
        return float(tok[:-2]) / 1000
    return float(tok.rstrip("s"))


class Kitty:
    def __init__(self, sock, typing):
        self.to, self.typing, self.wait_re, self.wait_timeout = f"unix:{sock}", typing, re.compile(r">$"), 90

    def rc(self, *a):
        r = subprocess.run(["kitty", "@", "--to", self.to, *a], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"kitty @ {a[0]}: {r.stderr.strip()}")
        return r.stdout

    def type(self, text, speed=None):
        delay = self.typing if speed is None else speed
        for ch in text:
            t0 = time.time()
            self.rc("send-text", "--", ch)
            time.sleep(max(0.0, delay - (time.time() - t0)))

    def key(self, name, count=1, speed=0.1):
        for _ in range(count):
            self.rc("send-key", name)
            time.sleep(speed)

    def wait(self, pattern=None, screen=False, timeout=None):
        pattern = re.compile(pattern) if pattern else self.wait_re
        end = time.time() + (timeout or self.wait_timeout)
        while time.time() < end:
            lines = [l.rstrip() for l in self.rc("get-text", "--extent", "screen").splitlines() if l.strip()]
            if lines and (any(map(pattern.search, lines)) if screen else pattern.search(lines[-1])):
                return
            time.sleep(0.2)
        raise TimeoutError("Wait timed out")


def run_line(k, line, clock):
    """Interpret one VHS command against kitty. Returns nothing; clock records Hide/Show."""
    line = line.strip()
    if not line or line.startswith("#"):
        return
    word, _, rest = line.partition(" ")
    if word == "Set":
        name, _, val = rest.partition(" ")
        if name == "WaitPattern":
            k.wait_re = re.compile(val.strip().strip("/"))
        elif name == "TypingSpeed":
            k.typing = seconds(val)
        elif name == "WaitTimeout":
            k.wait_timeout = seconds(val)
        return
    if word in ("Hide", "Show"):
        clock.append((word, time.time()))
        return
    if word == "Sleep":
        time.sleep(seconds(rest))
        return
    if word.startswith("Wait"):
        m = re.match(r"^Wait(\+Screen|\+Line)?(?:@(\S+))?\s*(?:/(.*)/)?\s*$", line)
        k.wait(m[3], m[1] == "+Screen", seconds(m[2]) if m[2] else None)
        return
    if word in ("Screenshot", "Output", "Require", "Source"):
        return
    m = re.match(r"^Type(?:@(\S+))?\s+(\"(?:[^\"\\]|\\.)*\"|'[^']*'|`[^`]*`)(.*)$", line)
    if m:
        k.type(m[2][1:-1], seconds(m[1]) if m[1] else None)
        if m[3].strip():
            run_line(k, m[3], clock)  # e.g. `Type "ls" Enter`
        return
    m = re.match(r"^(Ctrl|Alt|Shift)\+(\S+)(.*)$", line)
    if m:
        k.key(f"{m[1].lower()}+{m[2].lower()}")
        if m[3].strip():
            run_line(k, m[3], clock)
        return
    m = re.match(r"^(\w+)(?:@(\S+))?(?:\s+(\d+))?(.*)$", line)
    if m and m[1] in KEYS:
        k.key(KEYS[m[1]], int(m[3] or 1), seconds(m[2]) if m[2] else 0.1)
        if m[4].strip():
            run_line(k, m[4], clock)
        return
    print(f"  (real pass ignores: {line})")


def real(args):
    tape = Path(args.tape).resolve()
    sets, setup, beats = parse_tape(tape)
    out = tape.parent / "renders"
    out.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="film-real-"))
    sock, disp, procs = tmp / "kitty.sock", ":98", []
    env = dict(film_env(tape, args, real=True), DISPLAY=disp)
    env.pop("WAYLAND_DISPLAY", None)
    raw = tmp / "raw.mp4"
    try:
        procs.append(subprocess.Popen(["Xvfb", disp, "-screen", "0", "1920x1080x24", "-nolisten", "tcp"],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        time.sleep(1)
        procs.append(subprocess.Popen(["openbox", "--config-file", str(KIT / "ide" / "openbox-film.xml")],
                                      env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        time.sleep(1)
        procs.append(subprocess.Popen(
            ["kitty", "--listen-on", f"unix:{sock}", "-o", "allow_remote_control=socket-only",
             "-o", f"font_size={args.font_size}", "--directory", str(demo_dir(tape, args.demo)), "zsh", "-i"],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        k = Kitty(sock, 0.045)
        for _ in range(50):
            try:
                k.rc("ls")
                break
            except RuntimeError:
                time.sleep(0.2)
        time.sleep(2)  # starship and the rest of her zshrc
        ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "x11grab", "-framerate", "30",
                               "-video_size", "1920x1080", "-i", disp, "-c:v", "libx264", "-preset", "veryfast",
                               "-crf", "16", "-pix_fmt", "yuv420p", str(raw)], stdin=subprocess.PIPE)
        t0 = time.time()
        clock, marks = [], []
        for line in sets + setup:
            run_line(k, line, clock)
        for beat in beats:
            marks.append((beat, time.time()))
            print(f"[{beat['id']}]", flush=True)
            for line in beat["lines"]:
                run_line(k, line, clock)
        t_end = time.time()
        time.sleep(0.5)
        ff.communicate(b"q")
    finally:
        for p in reversed(procs):
            p.terminate()
        for p in procs:
            p.wait(timeout=10)
    # Hidden spans in recording time, then a map from recording time to cut time.
    hidden, start = [], None
    for word, t in clock:
        if word == "Hide" and start is None:
            start = t - t0
        elif word == "Show" and start is not None:
            hidden.append((start, t - t0))
            start = None
    if start is not None:
        hidden.append((start, t_end - t0 + 1))

    def cut(t):
        return t - sum(max(0, min(t, b) - a) for a, b in hidden)

    keep = " + ".join(f"between(t,{a:.3f},{b:.3f})" for a, b in hidden) or "0"
    stem = out / f"{tape.stem}-real"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-t", f"{t_end - t0:.3f}",
                    "-vf", f"select='not({keep})',setpts=N/FRAME_RATE/TB", "-c:v", "libx264", "-preset", "slow",
                    "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", f"{stem}.mp4"], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    starts = [cut(t - t0) for _, t in marks] + [cut(t_end - t0)]
    cues = [(b["id"], b["title"], starts[i], starts[i + 1]) for i, (b, _) in enumerate(marks)]
    print(f"{stem}.mp4  {starts[-1]:.1f}s")
    write_cues(stem, cues, storyboard_vo(tape))


# ------------------------------------------------------------- IDE takes

def encode(args_in, vf, out):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args_in, "-vf" if ";" not in vf else "-filter_complex", vf,
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(out)], check=True)


def ide(args):
    film = Path(args.film).resolve()
    r = film / "renders"
    raw, name = r / "take-raw.mp4", args.name or film.parent.name.split("_", 1)[-1]
    marks = [(l.split("\t")[0], float(l.split("\t")[1]) - args.trim)
             for l in (r / "take.marks").read_text().splitlines() if l.strip()]
    vo, focus = storyboard_vo(film), storyboard_vo(film, "focus")
    end = duration(raw) - args.trim
    cues = [(b, b, max(0.0, t), marks[i + 1][1] if i + 1 < len(marks) else end) for i, (b, t) in enumerate(marks)]
    stem = r / f"{name}-landscape"
    encode(["-ss", str(args.trim), "-i", str(raw)], "scale=1920:1080:flags=lanczos", f"{stem}.mp4")
    print(f"{stem}.mp4  {end:.1f}s")
    write_cues(stem, cues, vo)
    # Vertical: each beat zooms into its focus box, over a blurred copy of the frame.
    parts, seg = [], r / "vertical"
    seg.mkdir(exist_ok=True)
    for i, (bid, _, a, b) in enumerate(cues, 1):
        x, y, w, h = (int(v) for v in focus.get(bid, "0,0,2560,1440").split(","))
        part = seg / f"{i:02d}-{bid}.mp4"
        vf = (f"[0:v]split[a][b];"
              f"[a]scale=-2:1920,crop=1080:1920,boxblur=24:2,eq=brightness=-0.08[bg];"
              f"[b]crop={w}:{h}:{x}:{y},scale=1040:-2:flags=lanczos[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2")
        encode(["-ss", f"{a + args.trim:.3f}", "-to", f"{b + args.trim:.3f}", "-i", str(raw)], vf, part)
        parts.append(part)
    vstem = r / f"{name}-vertical"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f.name, "-c", "copy",
                    "-movflags", "+faststart", f"{vstem}.mp4"], check=True)
    os.unlink(f.name)
    vcues, t = [], 0.0
    for (bid, title, _, _), p in zip(cues, parts):
        d = duration(p)
        vcues.append((bid, title, t, t + d))
        t += d
    print(f"{vstem}.mp4  {t:.1f}s")
    write_cues(vstem, vcues, vo)


# --------------------------------------------------------------------- zoom
# The camera follows OpenScreen's zoom regions (src/components/video-editor/videoPlayback),
# so the headless render and the .openscreen project move the same way: an eased zoom-in
# that lands 0.5s into the region, a 1s zoom-out, and a 1s pan between regions less than
# 1.5s apart. OpenScreen only keeps its preset depths, so the scale snaps down to one.

DEPTHS = {1: 1.25, 2: 1.5, 3: 1.8, 4: 2.2, 5: 3.5, 6: 5.0}
OUT_MS, IN_MS, IN_OVERLAP_MS, CHAIN_GAP_MS, PAN_MS = 1015.05, 1015.05 * 1.5, 500, 1500, 1000


def bezier(x1, y1, x2, y2):
    """CSS cubic-bezier easing as a function of t."""
    def axis(a, b, u):
        return 3 * a * u * (1 - u) ** 2 + 3 * b * u * u * (1 - u) + u ** 3

    def ease(t):
        if t <= 0 or t >= 1:
            return min(1.0, max(0.0, t))
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if axis(x1, x2, mid) < t else (lo, mid)
        return axis(y1, y2, (lo + hi) / 2)
    return ease


EASE_ZOOM, EASE_PAN = bezier(0.16, 1, 0.3, 1), bezier(0.1, 0.0, 0.2, 1.0)


def zoom_regions(film, fmt, space, cues):
    """Storyboard zoom cells -> [(start_ms, end_ms, depth, cx, cy)].

    A cell is `;`-separated `<region> <from>-<to>`: seconds from the beat's start, `to`
    may be `end` or `end-N`. A region is a name from the `region` table (one box column
    per format, `-` to skip it in that format) or a literal `x,y,w,h`, in `space` pixels."""
    boxes = {k: v for k, v in storyboard_vo(film, fmt).items() if k}
    W, H = space
    out = []
    for bid, cell in storyboard_vo(film, "zoom").items():
        cue = cues.get(bid)
        if not cue or not cell.strip("`- "):
            continue
        a, b = cue
        for item in cell.strip("`").split(";"):
            name, span = item.split()
            box = boxes.get(name.strip("`"), name)
            if box.strip("`") in ("-", ""):
                continue
            x, y, w, h = (float(v) for v in box.strip("`").split(","))
            t0, t1 = span.split("-", 1)
            t1 = b - a - float(t1[4:] or 0) if t1.startswith("end") else float(t1)
            fit = min(W / w, H / h)
            depth = max([d for d, s in DEPTHS.items() if s <= fit] or [1])
            out.append(((a + float(t0)) * 1000, (a + t1) * 1000, depth, (x + w / 2) / W, (y + h / 2) / H))
    return sorted(out)


def camera(regions, ms):
    """(scale, cx, cy) at ms, before clamping the focus to the frame."""
    for (s0, e0, d0, x0, y0), (s1, e1, d1, x1, y1) in zip(regions, regions[1:]):
        if s1 - e0 <= CHAIN_GAP_MS and e0 <= ms <= max(s1, e0 + PAN_MS):
            k = EASE_PAN(min(1.0, (ms - e0) / PAN_MS))
            return (DEPTHS[d0] + (DEPTHS[d1] - DEPTHS[d0]) * k, x0 + (x1 - x0) * k, y0 + (y1 - y0) * k)
    best = (1.0, 0.5, 0.5, 0.0)
    for i, (s, e, d, x, y) in enumerate(regions):
        chained_in = i > 0 and s - regions[i - 1][1] <= CHAIN_GAP_MS
        chained_out = i + 1 < len(regions) and regions[i + 1][0] - e <= CHAIN_GAP_MS
        land = s + IN_OVERLAP_MS
        if s <= ms <= e and (chained_in or ms >= land):
            k = 1.0
        elif not chained_in and land - IN_MS <= ms < land:
            k = EASE_ZOOM((ms - land + IN_MS) / IN_MS)
        elif not chained_out and e < ms <= e + OUT_MS:
            k = 1 - EASE_ZOOM((ms - e) / OUT_MS)
        else:
            continue
        if k > best[3]:
            best = (1 + (DEPTHS[d] - 1) * k, 0.5 + (x - 0.5) * k, 0.5 + (y - 0.5) * k, k)
    return best[:3]


def zoom(args):
    from PIL import Image

    video = Path(args.video).resolve()
    stem = video.with_suffix("")
    film = Path(args.storyboard).resolve() if args.storyboard else video.parent.parent
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height,r_frame_rate", "-of", "csv=p=0", str(video)],
                           capture_output=True, text=True, check=True).stdout.strip().split(",")
    W, H = int(probe[0]), int(probe[1])
    num, den = probe[2].split("/")
    fps = float(num) / float(den)
    space = tuple(int(v) for v in args.space.split("x")) if args.space else (W, H)
    cues = {}
    for line in Path(f"{stem}.cues.tsv").read_text().splitlines()[1:]:
        f = line.split("\t")
        cues[f[0]] = (float(f[1]), float(f[2]))
    regions = zoom_regions(film, args.format, space, cues)
    if not regions:
        sys.exit(f"{film}/storyboard.md: no zoom cells for {args.format}")
    for s, e, d, x, y in regions:
        print(f"  {s / 1000:6.1f} to {e / 1000:6.1f}s  x{DEPTHS[d]}  at {x:.2f},{y:.2f}")

    project = {"version": 2, "media": {"screenVideoPath": str(video)}, "videoPath": str(video), "editor": {
        "zoomRegions": [{"id": f"zoom-{i}", "startMs": round(s), "endMs": round(e), "depth": d,
                         "focus": {"cx": round(x, 4), "cy": round(y, 4)}, "focusMode": "manual", "source": "manual"}
                        for i, (s, e, d, x, y) in enumerate(regions, 1)],
        "padding": 0, "borderRadius": 0, "shadowIntensity": 0, "showBlur": False, "motionBlurAmount": 0,
        "aspectRatio": "9:16" if H > W else "16:9", "exportQuality": "source", "exportFormat": "mp4"}}
    Path(f"{stem}.openscreen").write_text(json.dumps(project, indent=2) + "\n")

    out = Path(f"{stem}-zoom.mp4")
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", probe[2], "-i", "-", "-c:v", "libx264", "-preset", "slow",
                            "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
                           stdin=subprocess.PIPE)
    size, n = W * H * 3, 0
    while frame := dec.stdout.read(size):
        if len(frame) < size:
            break
        s, cx, cy = camera(regions, n / fps * 1000)
        if s > 1.001:
            half_w, half_h = 0.5 / s, 0.5 / s
            x0 = (min(max(cx, half_w), 1 - half_w) - half_w) * W
            y0 = (min(max(cy, half_h), 1 - half_h) - half_h) * H
            img = Image.frombuffer("RGB", (W, H), frame).transform(
                (W, H), Image.Transform.AFFINE, (1 / s, 0, x0, 0, 1 / s, y0), Image.Resampling.BICUBIC)
            frame = img.tobytes()
        enc.stdin.write(frame)
        n += 1
    enc.stdin.close()
    dec.wait()
    if enc.wait() or dec.returncode:
        sys.exit("ffmpeg failed")
    print(f"{out}  {n / fps:.1f}s\n{stem}.openscreen")


# ------------------------------------------------------------------- review

def sheet(args):
    video = Path(args.video)
    d = duration(video)
    n = int(d // args.every) + 1
    cols = 4
    rows = -(-n // cols)
    out = video.with_suffix(".sheet.png")
    vf = (f"fps=1/{args.every},scale=640:-2,"
          r"drawtext=text='%{pts\:hms}':x=8:y=8:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6,"
          f"tile={cols}x{rows}:padding=4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", vf, "-frames:v", "1", str(out)],
                   check=True)
    print(out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("tape")
    r.add_argument("--format", default="landscape", choices=["landscape", "vertical"])
    r.add_argument("--theme", default="spark", choices=[t.stem for t in (KIT / "themes").glob("*.json")])
    r.add_argument("--only", help="re-render these beat ids, reuse the other clips")
    r.add_argument("--demo", help="demo folder to film (default: the tape's parent's parent)")
    r.set_defaults(fn=render)
    q = sub.add_parser("real")
    q.add_argument("tape")
    q.add_argument("--font-size", default="16.5")
    q.add_argument("--demo")
    q.set_defaults(fn=real)
    i = sub.add_parser("ide")
    i.add_argument("film")
    i.add_argument("--trim", type=float, default=1.0, help="seconds cut from the start of the raw take")
    i.add_argument("--name")
    i.set_defaults(fn=ide)
    z = sub.add_parser("zoom")
    z.add_argument("video")
    z.add_argument("--format", default="landscape", choices=["landscape", "vertical"])
    z.add_argument("--space", help="WxH the storyboard boxes are measured in (default: the video's size)")
    z.add_argument("--storyboard", help="film folder with storyboard.md (default: the video's parent's parent)")
    z.set_defaults(fn=zoom)
    s = sub.add_parser("sheet")
    s.add_argument("video")
    s.add_argument("--every", type=float, default=3.0)
    s.set_defaults(fn=sheet)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
