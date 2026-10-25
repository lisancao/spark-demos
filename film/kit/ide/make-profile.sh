#!/usr/bin/env bash
# Build the IntelliJ film profile from Lisa's own config, once:
#   make-profile.sh <repo-root>      e.g. ~/spark-demos-main
# The profile is a copy, so filming never touches her IntelliJ settings. Only two
# plugins come along (IdeaVim, Cyberpunk Neon), and the copy differs in five places:
# the MCP server is off (it would clash with her running IDE's), the repo is trusted,
# Ctrl+F belongs to the IDE instead of IdeaVim, console soft wrap is on (long plan
# lines fit), and the UI renders at 2x so 2560x1440 lays out like 1280x720.
set -euo pipefail
kit="$(cd "$(dirname "$0")" && pwd)"
P="${FILM_IDE_PROFILE:-$kit/profile}"
repo="$(cd "${1:?usage: make-profile.sh <repo-root>}" && pwd)"
ver=IntelliJIdea2026.2
idea=/snap/intellij-idea-community/current/bin
[[ -e "$P" ]] && { echo "$P exists; delete it to rebuild" >&2; exit 1; }
mkdir -p "$P/plugins" "$P/system" "$P/log"
cp -a "$HOME/.config/JetBrains/$ver" "$P/config"
cp -a "$HOME/.local/share/JetBrains/$ver/IdeaVIM" "$HOME/.local/share/JetBrains/$ver/cyberpunk-neon-theme" "$P/plugins/"
cat >"$P/idea.properties" <<PROPS
idea.config.path=$P/config
idea.system.path=$P/system
idea.plugins.path=$P/plugins
idea.log.path=$P/log
PROPS
{ cat "$idea/idea64.vmoptions"; echo "-Dsun.java2d.uiScale=2"; echo "-Dide.ui.scale=1.0"; } >"$P/idea64.vmoptions"
python3 - "$P/config/options" "$repo" <<'PY'
import sys, pathlib, re
opts, repo = pathlib.Path(sys.argv[1]), sys.argv[2]
home = str(pathlib.Path.home())
def edit(name, fn):
    f = opts / name
    f.write_text(fn(f.read_text()))
edit("mcpServer.xml", lambda s: s.replace('name="enableMcpServer" value="true"', 'name="enableMcpServer" value="false"'))
edit("vim_settings.xml", lambda s: s.replace("<shortcut-conflicts />",
    '<shortcut-conflicts>\n      <shortcut-conflict owner="ide">\n'
    '        <text encoding="base64">Y3RybCBwcmVzc2VkIEY=</text>\n'  # "ctrl pressed F"
    '      </shortcut-conflict>\n    </shortcut-conflicts>'))
edit("editor.xml", lambda s: s if "USE_SOFT_WRAPS" in s else s.replace(
    '<component name="EditorSettings">', '<component name="EditorSettings">\n    <option name="USE_SOFT_WRAPS" value="CONSOLE" />', 1))
key = repo.replace(home, "$USER_HOME$", 1)
(opts / "trusted-paths.xml").write_text(
    '<application>\n  <component name="Trusted.Paths">\n    <option name="TRUSTED_PROJECT_PATHS">\n      <map>\n'
    f'        <entry key="{key}" value="true" />\n      </map>\n    </option>\n  </component>\n</application>\n')
PY
echo "profile: $P ($(du -sh "$P" | cut -f1))"
