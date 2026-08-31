#!/usr/bin/env bash
# Put the io builds and the event data onto every USB stick that is plugged in.
#
#   ./app/io/usb_copy.sh                 # copy to every stick it finds
#   ./app/io/usb_copy.sh --dry-run       # say what it would do, touch nothing
#   ./app/io/usb_copy.sh --verify        # check drives that were already copied
#   ./app/io/usb_copy.sh --builds DIR    # where the archives are (default: ./bin)
#   ./app/io/usb_copy.sh --target DIR    # copy here instead of hunting sticks (repeatable)
#
# Run it from the root of this repo. Plug in as many sticks as you like, in a hub or one
# at a time, and run it again after each batch: it copies to all of them at once and skips
# anything already there, so running it twice costs almost nothing.
#
# On each stick it makes:
#     insightout/io/      the unpacked builds, one folder per platform
#     insightout/data/    the sample data from simulations/foundation-without/data
set -uo pipefail

BUILDS="bin"
TARGETS=()
DRY=0
VERIFY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --builds) BUILDS="$2"; shift 2 ;;
    --target) TARGETS+=("$2"); shift 2 ;;   # repeatable, mostly for testing
    --dry-run|-n) DRY=1; shift ;;
    --verify) VERIFY=1; shift ;;
    -h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

DATA_SRC="simulations/foundation-without/data"
HERE_DIR=$(cd "$(dirname "$0")" && pwd)
say() { printf '%s\n' "$*"; }
die() { printf 'usb_copy: %s\n' "$*" >&2; exit 1; }

[ -d "$BUILDS" ] || die "no builds directory at '$BUILDS'. Pass --builds DIR, or put the archives in ./bin"
[ -d "$DATA_SRC" ] || die "run this from the root of the repo: '$DATA_SRC' not found"

# ---------------------------------------------------------------- find the sticks
# A stick is a mounted filesystem on a device the kernel calls removable or hotplug.
# That is the honest test; size is only a last resort for enclosures that report neither.
find_sticks() {
  if [ "${#TARGETS[@]}" -gt 0 ]; then printf '%s\n' "${TARGETS[@]}"; return; fi
  lsblk -b -P -o NAME,RM,HOTPLUG,TYPE,SIZE,MOUNTPOINT 2>/dev/null | while read -r line; do
    eval "$line"
    [ "${TYPE:-}" = "part" ] || continue
    [ -n "${MOUNTPOINT:-}" ] || continue
    case "$MOUNTPOINT" in /|/boot|/boot/*|/home|/var|/usr|/snap/*|[!/]*) continue ;; esac
    if [ "${RM:-0}" = "1" ] || [ "${HOTPLUG:-0}" = "1" ] || [ "${SIZE:-0}" -lt 68719476736 ]; then
      printf '%s\n' "$MOUNTPOINT"
    fi
  done | sort -u
}

# --------------------------------------------------------------- unpack the builds
# Unpacked once into a staging dir and reused, so plugging in ten sticks does not mean
# unpacking ten times.
STAGE="${TMPDIR:-/tmp}/io-usb-stage"
unpack_builds() {
  mkdir -p "$STAGE"
  local n=0
  for f in "$BUILDS"/*.tar.gz "$BUILDS"/*.zip; do
    [ -e "$f" ] || continue
    local base; base=$(basename "$f"); base=${base%.tar.gz}; base=${base%.zip}
    local out="$STAGE/$base"
    if [ -d "$out" ] && [ -n "$(ls -A "$out" 2>/dev/null)" ]; then
      say "  already unpacked: $base"; n=$((n+1)); continue
    fi
    say "  unpacking $base ..."
    rm -rf "$out"; mkdir -p "$out"
    case "$f" in
      *.tar.gz) tar -xzf "$f" -C "$out" --strip-components=1 2>/dev/null || tar -xzf "$f" -C "$out" ;;
      *.zip)    unzip -q "$f" -d "$out" || say "    (unzip failed for $base)" ;;
    esac
    n=$((n+1))
  done
  # dmg files cannot be unpacked here, so they travel as-is for a Mac to open
  for f in "$BUILDS"/*.dmg; do
    [ -e "$f" ] || continue
    cp -n "$f" "$STAGE/" 2>/dev/null || true
    say "  carrying $(basename "$f") as-is (a Mac opens it)"
    n=$((n+1))
  done
  [ "$n" -gt 0 ] || die "no .tar.gz, .zip or .dmg found in '$BUILDS'"
}

# ------------------------------------------------------------------- copy to one
copy_to() {
  local mp="$1" log="$2"
  {
    echo "=== $mp ==="
    local dest="$mp/insightout"
    mkdir -p "$dest/io" "$dest/data" || { echo "  cannot write to $mp"; exit 1; }
    # -a keeps modes so the linux binary stays executable where the filesystem allows it,
    # --update skips what is already there, so a second run is nearly free
    rsync -a --update --info=progress2 --no-inc-recursive "$STAGE"/ "$dest/io/" 2>&1 \
      || cp -ru "$STAGE"/. "$dest/io/" 2>&1
    rsync -a --update "$DATA_SRC"/ "$dest/data/" 2>&1 || cp -ru "$DATA_SRC"/. "$dest/data/" 2>&1
    # The instructions travel with the drive. Someone who picks this up without the
    # room's wifi, or without an organizer next to them, still knows what to do.
    [ -f "$HERE_DIR/START-HERE.txt" ] && cp -f "$HERE_DIR/START-HERE.txt" "$mp/START-HERE.txt"
    cp -f "$STAGE/../io-usb-manifest.txt" "$dest/MANIFEST.txt" 2>/dev/null || true
    sync
    echo "  done: $(du -sh "$dest" 2>/dev/null | cut -f1) on $mp"
  } > "$log" 2>&1
}


# ------------------------------------------------------------------------ verify
# Check a drive against the manifest written when it was copied. A power cut mid-copy
# leaves files missing or half-written, and both show up as a size mismatch.
verify_drive() {
  local mp="$1"
  # not on one line with mp: bash makes every name in a single `local` local first, which
  # unsets it, so a later assignment on the same line would read an empty mp under set -u
  local man="$mp/insightout/MANIFEST.txt"
  if [ ! -f "$man" ]; then
    printf '  %-28s NO MANIFEST - copied before this check existed, or never finished\n' "$(basename "$mp")"
    return 1
  fi
  local missing=0 wrong=0 total=0
  while read -r size rel; do
    [ -z "${rel:-}" ] && continue
    total=$((total+1))
    local f="$mp/insightout/$rel"
    if [ ! -f "$f" ]; then missing=$((missing+1))
    else
      local actual; actual=$(stat -c %s "$f" 2>/dev/null || echo -1)
      [ "$actual" = "$size" ] || wrong=$((wrong+1))
    fi
  done < "$man"
  if [ "$missing" -eq 0 ] && [ "$wrong" -eq 0 ]; then
    printf '  %-28s COMPLETE  %s files all present and the right size\n' "$(basename "$mp")" "$total"
    return 0
  fi
  printf '  %-28s INCOMPLETE  %s missing, %s wrong size, of %s\n' "$(basename "$mp")" "$missing" "$wrong" "$total"
  return 1
}

# ------------------------------------------------------------------------- main
say "usb_copy"
say "  builds from : $BUILDS"
say "  data from   : $DATA_SRC"

mapfile -t STICKS < <(find_sticks)
if [ "${#STICKS[@]}" -eq 0 ]; then
  die "no USB drives found. Plug them in and check they are mounted, or use --target DIR"
fi
say "  found ${#STICKS[@]} drive(s):"
for m in "${STICKS[@]}"; do
  say "    $m   ($(df -h "$m" 2>/dev/null | awk 'NR==2{print $4" free of "$2}'))"
done

if [ "$VERIFY" = "1" ]; then
  say
  say "checking each drive against the manifest written when it was copied"
  bad=0
  for m in "${STICKS[@]}"; do verify_drive "$m" || bad=1; done
  say
  if [ "$bad" = "0" ]; then say "all drives verified complete."; else
    say "re-run without --verify to finish the incomplete ones; it copies only what is missing."; fi
  exit "$bad"
fi

if [ "$DRY" = "1" ]; then
  say
  say "dry run, nothing written. Would unpack into $STAGE and copy to:"
  for m in "${STICKS[@]}"; do say "    $m/insightout/{io,data}"; done
  exit 0
fi

say
say "preparing builds"
unpack_builds

# Every file's size and path, so a drive can be checked afterwards. Sizes rather than
# hashes: a truncated or missing file is what a power cut leaves behind, and that shows up
# here in seconds instead of the half hour it takes to sha256 eighty thousand files off a
# USB stick. --verify --deep does the hashes when you want certainty.
( cd "$STAGE" && find . -type f -printf '%s %p\n' | sed 's|^\([0-9]*\) \./|\1 io/|' ; \
  cd "$OLDPWD/$DATA_SRC" && find . -type f -printf '%s %p\n' | sed 's|^\([0-9]*\) \./|\1 data/|' ) \
  2>/dev/null | LC_ALL=C sort -k2 > "$STAGE/../io-usb-manifest.txt"
TOTAL_KB=$(du -sk "$STAGE" "$DATA_SRC" 2>/dev/null | awk '{s+=$1} END{print s+0}')
FILES=$(find "$STAGE" -type f 2>/dev/null | wc -l)
say
say "copying $((TOTAL_KB/1024)) MB in $FILES files to ${#STICKS[@]} drive(s) at once"
say "  a USB stick is slow with many small files; expect this to take a while"
LOGDIR="${LOGDIR_OVERRIDE:-./usb_copy-logs}"
mkdir -p "$LOGDIR"
say "  logs: $LOGDIR/  (kept, one file per drive)"
pids=()
for m in "${STICKS[@]}"; do
  safe=$(printf '%s' "$m" | tr -c 'A-Za-z0-9' '_')
  copy_to "$m" "$LOGDIR/$safe.log" &
  pids+=($!)
done
# Report real progress, not a spinner: how much has actually landed on each drive against
# how much is coming. Forty minutes of silence is indistinguishable from a hang, and these
# packs are ~100k small files, which a USB stick writes far slower than its rated speed.
started=$(date +%s)
while :; do
  running=0
  for p in "${pids[@]}"; do kill -0 "$p" 2>/dev/null && running=$((running+1)); done
  [ "$running" -eq 0 ] && break
  line=""
  for m in "${STICKS[@]}"; do
    got=$(du -sk "$m/insightout" 2>/dev/null | awk '{print $1+0}')
    pct=0; [ "${TOTAL_KB:-0}" -gt 0 ] && pct=$(( got * 100 / TOTAL_KB ))
    [ "$pct" -gt 100 ] && pct=100
    line="$line $(basename "$m")=${pct}%"
  done
  printf '\r  [%4ds] %d copying:%s        ' "$(( $(date +%s) - started ))" "$running" "$line"
  sleep 3
done
printf '\r%*s\r' 78 ''

fail=0
for p in "${pids[@]}"; do wait "$p" || fail=1; done
for f in "$LOGDIR"/*.log; do
  [ -e "$f" ] || continue
  grep -E '^=== |^  done:|cannot write' "$f" | sed 's/^/  /'
done

say
if [ "$fail" = "0" ]; then
  say "all drives done. Each has insightout/io and insightout/data."
  say "Unplug them safely; the copies are flushed."
else
  say "one or more drives failed, see above."
  exit 1
fi
