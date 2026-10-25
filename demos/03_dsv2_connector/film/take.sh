#!/usr/bin/env bash
# The DSv2 pushdown film: IntelliJ under the debugger, on the film display (:99).
# Storyboard: storyboard.md. Kit: film/kit/ide (see film/README.md).
#   take.sh prep     off camera: reset IntelliJ to the starting state, screenshot renders/prep.png
#   take.sh dry      run the take without recording; screenshot each beat as it starts
#   take.sh record   record renders/take-raw.mp4 and renders/take.marks
# Then: film/kit/film.py ide demos/03_dsv2_connector/film
# Starting state: BeforeAfterDemo.java open at line 75 (zt), project tree and Debug
# hidden, no breakpoints, CsvScanBuilder.java closed. Click positions assume the
# default tool window layout of a fresh launch (a dragged panel height does not
# survive a restart), so restart IntelliJ between takes.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
mode="${1:-dry}"
source "$here/../../../film/kit/ide/take-lib.sh"

if [[ "$mode" == prep ]]; then
  # A fresh launch of the film profile reopens README.md with the project tree showing
  # and no breakpoints; prep turns that (or a used IDE) into the starting state.
  wait_window 03_dsv2_connector
  xdotool key Escape Escape
  xdotool key ctrl+shift+n; sleep 1; xdotool type BeforeAfterDemo; sleep 1.5; xdotool key Return; sleep 2
  # Balloons (the Maven prompt on every launch) move around, so no clicks on them.
  vimaction ClearAllNotifications Stop Debugger.RemoveAllBreakpoints CloseAllEditorsButActive
  vimaction ActivateProjectToolWindow; xdotool key shift+Escape; sleep 0.8  # focus it, then hide it
  xdotool key Escape; keys 75G; keys zt
  sleep 1.5; keys zt   # a just-opened file restores its scroll late; frame it again
  xdotool mousemove 1700 1250
  import -window root -resize 1600x "$here/renders/prep.png"
  exit 0
fi

start_recording
xdotool mousemove 1700 1250

beat open          # the V2 query and the demo's own note about the plan
hold 13

beat goto          # to the connector's ScanBuilder
xdotool key ctrl+shift+n; hold 0.8
keys CsvScanBuilder; hold 1.5
xdotool key Return; hold 1.5
xdotool key Escape
keys 50G; keys zt; hold 1.5

beat contract      # the javadoc: return the filters you do NOT handle
hold 13

beat breakpoint    # break once the connector has sorted Spark's filters
keys 70G; hold 0.6
xdotool key ctrl+F8; hold 3

beat debug         # run the demo under the debugger; Spark plans and stops here
xdotool key shift+F9
hold 6             # JVM start, Spark session, the first query reaches the breakpoint
# The debugger recentres on line 70; bring the whole loop back into view.
glide 1500 600; xdotool click 1; hold 0.3
keys 61G; keys zt; keys 70G; hold 3

beat variables     # what Spark offered, what the connector kept
glide 700 1178; xdotool click 1; hold 0.8
xdotool key Right; hold 1.5
xdotool key Down Down Down; hold 0.5
xdotool key Right; hold 1.5
xdotool key Down Down; hold 0.5
xdotool key Right; hold 12

beat plan          # finish the run and find the plan line
glide 1500 600; xdotool click 1; hold 0.3
keys 70G; xdotool key ctrl+F8; hold 0.8   # remove the breakpoint so the run finishes
xdotool key F9; hold 4
glide 1042 1024; xdotool click 1; hold 1      # Console tab
glide 1600 1250; xdotool click 1; hold 0.3    # into the console text, so Ctrl+F searches it
xdotool key ctrl+f; hold 0.6
keys 'pushedFilters=1)'; hold 12              # first match: the V2 plan
