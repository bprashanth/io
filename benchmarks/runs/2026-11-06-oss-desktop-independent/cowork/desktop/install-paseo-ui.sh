#!/bin/sh
# Install Idli's patched Paseo app UI (P13 side-by-side chats, P14 focus ring; desktop/paseo-idli-split.patch) on the
# laptop. Paseo's desktop shell loads its UI from /opt/Paseo/resources/app-dist; we point that at a folder we own,
# once (sudo), so later updates and rollbacks need no sudo.
#   install-paseo-ui.sh [install|off|status]     (DGX=user@host overrides the build host)
set -e
DGX=${DGX:-beeps@gx10-0a47.tail5ef239.ts.net}
BUILD=${BUILD:-paseo-app-dist-0.15.2-idli6}
RES=/opt/Paseo/resources
OURS=${IDLI_HOME:-$HOME/idli-insights}/paseo/app-dist
CFG=${IDLI_HOME:-$HOME/idli-insights}/config/ui.json
case "${1:-install}" in
  status)
    ls -ld "$RES/app-dist"; cat "$CFG" 2>/dev/null; echo ;;
  off)  # back to stock Paseo's UI and two separate workspaces
    printf '{"split": false}\n' > "$CFG"
    [ -L "$RES/app-dist" ] && [ -d "$RES/app-dist.orig" ] && echo "run: sudo rm $RES/app-dist && sudo mv $RES/app-dist.orig $RES/app-dist" || true
    echo "split off" ;;
  install)
    tmp=$(mktemp -d)
    scp -q "$DGX:idli-builds/$BUILD.tgz" "$tmp/b.tgz"
    rm -rf "$OURS.new" && mkdir -p "$OURS.new" && tar -C "$OURS.new" -xzf "$tmp/b.tgz" && rm -rf "$tmp"
    [ -f "$OURS.new/index.html" ] || { echo "the build has no index.html"; exit 1; }
    rm -rf "$OURS.old"; [ -d "$OURS" ] && mv "$OURS" "$OURS.old"; mv "$OURS.new" "$OURS"
    echo "$BUILD" > "$OURS/IDLI_BUILD"
    if [ "$(readlink "$RES/app-dist")" != "$OURS" ]; then
      echo "One-time step (needs your password): point Paseo at the Idli build:"
      echo "  sudo mv $RES/app-dist $RES/app-dist.orig && sudo ln -s $OURS $RES/app-dist"
      echo "then rerun this script."
      exit 2
    fi
    mkdir -p "$(dirname "$CFG")"; printf '{"split": true}\n' > "$CFG"
    echo "installed $BUILD; restart Paseo (desktop/idli-launch.sh) to load it" ;;
esac
