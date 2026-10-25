# Filming the demos

Scripted, headless recordings of the demos running for real: a terminal film made with
[VHS](https://github.com/charmbracelet/vhs), or IntelliJ driven on a hidden X display.
Nothing appears on the desktop, and every take can be re-rendered from its script.
Renders are ignored by git (`**/film/renders/`); only the scripts and storyboards are
committed.

Each film lives next to its demo:

```
demos/NN_<feature>/film/
  storyboard.md        the story, one row per beat: what shows, the VO line, the vertical focus
  <name>.tape          terminal film (VHS), or
  take.sh              IDE film (xdotool on the film display)
  renders/             ignored: clips, cuts, cue sheets, VO guides, contact sheets
film/kit/
  film.py              render, real pass, IDE finishing, contact sheets
  themes/              spark (default), nullstone (Lisa's kitty theme)
  formats/             landscape 1920x1080, vertical 1080x1920
  nvim-film.lua        film-only nvim config (reuses the installed plugins)
  ide/                 film display, IntelliJ film profile builder, take helpers
```

## What a film produces

For every format, a cut plus two files for whoever edits it:

- `<name>-<format>.cues.tsv`: each beat's start, end and length, with its title and VO line.
- `<name>-<format>.vo.srt`: the VO lines as subtitles on the beat timings. It's a guide
  track for recording a voiceover or splicing into a longer video, not captions to burn
  in: when the script changes, the SRT is regenerated from the storyboard.

The terminal films also keep one clip per beat in `renders/<format>/`, so an editor can
stretch or drop a beat without re-cutting the whole film. The runner warns when a beat
is shorter than its VO line at 150 words a minute.

## Terminal films

```bash
film/kit/film.py render demos/01_metrics_views/film/metric_views.tape                    # landscape
film/kit/film.py render demos/01_metrics_views/film/metric_views.tape --format vertical
film/kit/film.py render <tape> --only define       # re-render one beat, reuse the other clips
film/kit/film.py real   demos/01_metrics_views/film/metric_views.tape                    # Lisa's own kitty
film/kit/film.py zoom   demos/01_metrics_views/film/renders/metric_views-landscape.mp4   # dynamic zoom
film/kit/film.py sheet  demos/01_metrics_views/film/renders/metric_views-landscape.mp4   # review
```

A tape is plain VHS plus two conventions. Everything before the first `# beat: <id> |
<title>` line is setup that runs hidden at the start of every clip, and each beat is
rendered as its own clip. Size, font and theme come from `formats/` and `themes/`.
`--demo <dir>` films a different checkout of the demo (one that has its `.venv`).

**Code beside its output.** In the film nvim config, `:Run` runs the open file in a
terminal split (beside the code in landscape, below it in vertical), so the query stays
on screen while its result arrives. The example beats open each script on its queries
and then `:Run` it.

**Dynamic zoom.** `film.py zoom <cut>` reads the storyboard's `zoom` column (a named
region and the seconds into the beat it holds) and the cut's cue sheet, and writes
`<cut>-zoom.mp4` plus `<cut>.openscreen`. The camera copies OpenScreen's zoom regions:
an eased zoom-in, a pan straight to the next region when the gap is under 1.5s, and a
1s zoom-out, at OpenScreen's preset scales (1.25 to 5). The `.openscreen` file is the
same zooms as an OpenScreen 1.5 project (`~/Downloads/Openscreen-Linux-1.5.0.AppImage`,
Open Project), for adjusting by hand and exporting with its own effects. IDE cuts pass
`--space 2560x1440` so the boxes stay in the film display's pixels.

**OpenScreen's own render.** `film/kit/openscreen/openscreen.sh <project> <out.mp4>`
opens a `.openscreen` project in OpenScreen 1.5 on a hidden display and exports it, so
its backdrop, drop shadow, rounded corners and motion blur are in the film. It drives
the editor over the DevTools protocol (`export.mjs`) and types paths into its GTK file
dialogs. Set the look in the project's `editor` block: `wallpaper` (an image path, a
colour or a CSS gradient), `padding` (0 to 100), `borderRadius` (0 to 64),
`shadowIntensity` and `motionBlurAmount` (0 to 1).

```bash
film/kit/openscreen/openscreen.sh demos/03_dsv2_connector/film/renders/dsv2_pushdown-styled.openscreen \
    demos/03_dsv2_connector/film/renders/dsv2_pushdown-openscreen.mp4
```

**The real pass** types the same tape into Lisa's kitty with her own zsh, prompt,
plugins and aliases, on a hidden display, and cuts out the hidden sections. It's how
you catch what VHS hides: the first run showed that her zsh highlighting turns the
comment captions nearly invisible, the prompt shows the branch and dirty state, and
autosuggestions flash old commands while a line is being typed.

## IDE films

```bash
film/kit/ide/make-profile.sh ~/spark-demos-main       # once: copy of her IntelliJ config
film/kit/ide/ide-display.sh start ~/spark-demos-main/demos/03_dsv2_connector
demos/03_dsv2_connector/film/take.sh prep             # reset to the starting state
demos/03_dsv2_connector/film/take.sh dry              # screenshot each beat, no recording
demos/03_dsv2_connector/film/take.sh record
film/kit/film.py ide demos/03_dsv2_connector/film --name dsv2_pushdown
film/kit/ide/ide-display.sh stop
```

Film from a checkout on the branch the film should show (the IDE toolbar shows it).
Restart IntelliJ before each take: a fresh launch of the film profile comes back in
the same state, while some toggles persist within a session.

The vertical IDE cut zooms into each beat's `focus` box (from the storyboard) over a
blurred copy of the whole frame.

## Requirements

`vhs` and `ttyd` (on PATH), `ffmpeg`, `Xvfb`, `openbox`, `xdotool`, ImageMagick
`import`, kitty for the real pass, and the IntelliJ snap for IDE films. `film.py zoom`
needs Pillow. The OpenScreen export needs node 22 (for its built-in WebSocket),
`dbus-run-session`, a Vulkan driver, and the OpenScreen 1.5.0 AppImage. The nvim config
reuses plugins from `~/.local/share/nvim/lazy` and never installs any.
