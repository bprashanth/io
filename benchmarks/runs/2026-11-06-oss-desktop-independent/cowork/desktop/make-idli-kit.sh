#!/usr/bin/env bash
# Build the Idli kit: Idli's code (cowork/) from TRACKED files only (git archive, so no .venv, logs, tokens or
# test downloads can slip in), the private model's settings template, and the installer.
#   make-idli-kit.sh <version> <out dir>       run from anywhere inside the io checkout
# Output: <out>/idli-kit-<version>.tar.gz and .zip, each holding idli-kit/cowork/... and idli-kit/README.txt.
set -euo pipefail
VERSION=${1:?version}
OUT=$(mkdir -p "${2:?out dir}" && cd "$2" && pwd)
ROOT=$(git rev-parse --show-toplevel)
REL=benchmarks/runs/2026-11-06-oss-desktop-independent
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cd "$ROOT"
git archive --format=tar HEAD "$REL/cowork" "$REL/laptop/claude-t4gc-settings.json" | tar -x -C "$WORK"
mkdir -p "$WORK/idli-kit"
mv "$WORK/$REL/cowork" "$WORK/idli-kit/cowork"
cp "$WORK/$REL/laptop/claude-t4gc-settings.json" "$WORK/idli-kit/cowork/desktop/claude-t4gc-settings.json"
# Development-only material stays out of the kit.
rm -rf "$WORK/idli-kit/cowork/tests" "$WORK/idli-kit/cowork/HOME_SHOTS" "$WORK/idli-kit/cowork"/*_DONE.md
# Refuse to ship anything that looks like a credential.
if grep -rIlE --exclude=make-idli-kit.sh 'GOCSPX-|sk-ant-(api|oat)[0-9]{2}-[A-Za-z0-9_-]{10}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"client_secret"\s*:\s*"[^"<]{8,}"' \
     "$WORK/idli-kit"; then
  echo "make-idli-kit: refusing, the files above look like credentials" >&2; exit 1
fi
cat > "$WORK/idli-kit/README.txt" <<EOF
Idli kit $VERSION (alpha)

1. Install the Idli build of Paseo for your computer and open it once.
2. Install Claude Code, Python 3.10+, Node 20+ and npm.
3. Run:  python3 idli-kit/cowork/desktop/install-idli.py --token <the token file the owner gave you>
4. Quit and reopen Paseo.

Linux and macOS only in this alpha. Full notes: docs/idli-alpha-release.md in the io repo.
EOF
( cd "$WORK" && tar -czf "$OUT/idli-kit-$VERSION.tar.gz" idli-kit && \
  python3 -c "import shutil,sys; shutil.make_archive(sys.argv[1], 'zip', '.', 'idli-kit')" "$OUT/idli-kit-$VERSION" )
ls -lh "$OUT/idli-kit-$VERSION".*
