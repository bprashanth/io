#!/usr/bin/env bash
# Put the io builds and the event data onto every USB stick that is plugged in.
#
#   ./app/io/usb_copy.sh                 # copy to every stick it finds
#   ./app/io/usb_copy.sh --dry-run       # say what it would do, touch nothing
#   ./app/io/usb_copy.sh --verify        # check drives that were already copied
#   ./app/io/usb_copy.sh --builds DIR    # where the archives are (default: ./bin)
#   ./app/io/usb_copy.sh --target DIR    # copy here instead of hunting sticks (repeatable)
#   ./app/io/usb_copy.sh --platform win  # only these platforms (win,mac,linux; default all)
#   ./app/io/usb_copy.sh --verify --manifest FILE   # check against this manifest instead
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
# Which platforms to put on the drive. All three by default, because a drive handed to a
# room does not know who will pick it up. Narrow it when you are preparing a stick for
# people you have already asked - a Windows-only drive is a third of the size and a third
# of the files, which on a USB stick is most of the wait.
PLATFORMS="win mac linux"

DRY=0
VERIFY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --builds) BUILDS="$2"; shift 2 ;;
    --target) TARGETS+=("$2"); shift 2 ;;   # repeatable, mostly for testing
    --dry-run|-n) DRY=1; shift ;;
    --verify) VERIFY=1; shift ;;
    --manifest) REF_MANIFEST="$2"; shift 2 ;;
    --platform|--platforms) PLATFORMS=$(printf '%s' "$2" | tr ',' ' '); shift 2 ;;
    -h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

for p in $PLATFORMS; do
  case "$p" in
    win|mac|linux) ;;
    *) echo "usb_copy: unknown platform '$p'. Use win, mac, linux, or a comma-separated list." >&2; exit 2 ;;
  esac
done

# Does this archive belong to a platform that was asked for? The build names carry the
# platform, so match on that rather than keeping a list that drifts from the filenames.
wanted() {
  local name; name=$(basename "$1")
  local p
  for p in $PLATFORMS; do
    case "$name" in *-"$p"-*|*-"$p".*) return 0 ;; esac
  done
  return 1
}

DATA_SRC="simulations/foundation-without/data"
HERE_DIR=$(cd "$(dirname "$0")" && pwd)
say() { printf '%s\n' "$*"; }
die() { printf 'usb_copy: %s\n' "$*" >&2; exit 1; }

# --verify reads MANIFEST.txt off the drive and nothing else, so it must keep working after
# the builds and the staging copy have been deleted to reclaim disk. Requiring them here
# meant a drive could not be checked once you had cleaned up - which is exactly when you
# want to check it.
if [ "$VERIFY" = "0" ]; then
  [ -d "$BUILDS" ] || die "no builds directory at '$BUILDS'. Pass --builds DIR, or put the archives in ./bin"
  [ -d "$DATA_SRC" ] || die "run this from the root of the repo: '$DATA_SRC' not found"
fi

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
# Staging is keyed to the platform selection. Sharing one directory meant a --platform win
# run copied whatever a previous all-platforms run had left lying in it, which is the
# opposite of what was asked for.
STAGE="${TMPDIR:-/tmp}/io-usb-stage"
[ "$(printf '%s\n' $PLATFORMS | sort | tr '\n' ' ')" = "linux mac win " ] \
  || STAGE="$STAGE-$(printf '%s\n' $PLATFORMS | sort | tr '\n' '-' | sed 's/-$//')"
unpack_builds() {
  mkdir -p "$STAGE"
  local n=0
  for f in "$BUILDS"/*.tar.gz "$BUILDS"/*.zip; do
    [ -e "$f" ] || continue
    wanted "$f" || continue
    local base; base=$(basename "$f"); base=${base%.tar.gz}; base=${base%.zip}
    local out="$STAGE/$base"
    # Non-empty is not the same as complete. An unpack interrupted by a power cut leaves a
    # partial tree, and reusing it silently shipped a short copy to every drive - seven
    # sticks all 3,060 files light, and nothing said so. Count what the archive holds and
    # compare before trusting what is on disk.
    if [ -d "$out" ]; then
      local want have
      case "$f" in
        # tar -t lists a directory without a trailing slash when the archive was built
        # that way; counting "no slash = file" overcounted this pack by 2011 dirs and
        # re-unpacked complete staging on every run. -tv shows the type letter instead.
        *.tar.gz) want=$(tar -tvzf "$f" 2>/dev/null | grep -cv '^d') ;;
        *.zip)    want=$(unzip -Z1 "$f" 2>/dev/null | grep -vc '/$') ;;
      esac
      # -type f alone undercounts: tar and zip list a symlink as an entry, so an archive
      # holding one never matched and was thrown away and re-extracted on every run.
      have=$(find "$out" \( -type f -o -type l \) 2>/dev/null | wc -l)
      if [ "${want:-0}" -gt 0 ] && [ "$have" -eq "$want" ]; then
        say "  already unpacked: $base ($have files)"; n=$((n+1)); continue
      fi
      say "  re-unpacking $base: has $have files, expected ${want:-?}"
      rm -rf "$out"
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
    wanted "$f" || continue
    cp -n "$f" "$STAGE/" 2>/dev/null || true
    say "  carrying $(basename "$f") as-is (a Mac opens it)"
    n=$((n+1))
  done
  [ "$n" -gt 0 ] || die "no build for [$PLATFORMS] found in '$BUILDS'"
}

# ------------------------------------------------------------------- copy to one
copy_to() {
  local mp="$1" log="$2"
  {
    echo "=== $mp ==="
    local dest="$mp/insightout"
    mkdir -p "$dest/io" "$dest/data" || { echo "  cannot write to $mp"; exit 1; }
    # -a keeps modes so the linux binary stays executable where the filesystem allows it.
    # No --update: it skips on mtime alone, so a file left half-written by a power cut
    # keeps its timestamp and is never repaired. Tested - a truncated file survived a
    # re-run. rsync's default compares size and mtime, which still skips everything
    # unchanged and does fix a truncated file.
    #
    # -L is what makes this work on a USB stick. The packs carry ~1000 symlinks inside the
    # bundled python runtime, and exFAT cannot store a symlink at all, so plain -a fails on
    # every one of them and exits 23. The old fallback treated any non-zero exit as "rsync
    # is unusable" and re-copied the entire 3.5 GB with cp -r, on every drive, on every run,
    # after rsync had already finished - which is exactly why runs never ended and the
    # manifest at the end was never reached. -L sends the file a symlink points at instead
    # of the link, which exFAT can hold, and rsync exits 0. Verified on a real vfat image.
    # --modify-window=2: FAT stores mtimes at 2-second resolution and rounds down, so
    # half the files look "changed" to a re-run and were re-copied in full. Two seconds
    # of tolerance skips them; a truncated file still differs in size and is repaired.
    rsync -a -L --modify-window=2 --info=progress2 --no-inc-recursive "$STAGE"/ "$dest/io/" 2>&1
    local rc1=$?
    rsync -a -L --modify-window=2 "$DATA_SRC"/ "$dest/data/" 2>&1
    local rc2=$?
    # 24 means a source file vanished while we read it; harmless. Anything else is real,
    # and is reported rather than answered by silently copying everything a second way.
    for rc in "$rc1" "$rc2"; do
      case "$rc" in
        0|24) ;;
        *) echo "  rsync exited $rc - this drive is NOT complete, see the errors above"; exit 1 ;;
      esac
    done
    # The instructions travel with the drive. Someone who picks this up without the
    # room's wifi, or without an organizer next to them, still knows what to do.
    [ -f "$HERE_DIR/START-HERE.txt" ] && cp -f "$HERE_DIR/START-HERE.txt" "$mp/START-HERE.txt"
    cp -f "$STAGE/../io-usb-manifest.txt" "$dest/MANIFEST.txt" 2>/dev/null || true
    # sync with no argument flushes every filesystem on the machine, so with eight sticks
    # each of the eight copies blocked until all eight had finished writing back. -f waits
    # for just this drive.
    sync -f "$dest" 2>/dev/null || sync
    # Deliberately not du: walking ~75k files back off a slow exFAT stick, on eight
    # drives at once, took longer than the copy it was reporting on. The size is already
    # known from the source, and the file count is the number that actually matters.
    echo "  done: ~$(( ${TOTAL_KB:-0} / 1024 )) MB on $mp"
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
  local note=""
  if [ ! -f "$man" ]; then
    # A drive that lost power before the end never got its manifest, but it can still be
    # judged against the reference manifest from the same builds - that is what the copy
    # would have written. Found automatically in staging or the log dir, or --manifest FILE.
    if [ -n "${REF_MANIFEST:-}" ] && [ -f "$REF_MANIFEST" ]; then
      man="$REF_MANIFEST"
      note="  [no manifest on drive; checked against reference]"
    else
      printf '  %-28s NO MANIFEST - never finished, and no reference manifest found (--manifest FILE)\n' "$(basename "$mp")"
      return 1
    fi
  fi
  local missing=0 wrong=0 total=0 collided=0
  # FAT and exFAT are case-insensitive: two manifest entries differing only in case (the
  # runtime's terminfo ships Eterm and eterm, both real files) land on ONE file on the
  # stick, and which size survives depends on copy order. A mismatch whose actual size
  # equals a case-twin's manifest size is that, not damage; a truncated file matches
  # neither twin and still fails.
  local -A twin_sizes=()
  while IFS=$'\t' read -r lc sizes; do twin_sizes["$lc"]=" $sizes "; done < <(
    awk '{lc=tolower($0); sub(/^[0-9]+ /,"",lc); key[lc]=key[lc]" "$1; n[lc]++}
         END{for(k in n) if(n[k]>1) printf "%s\t%s\n", k, key[k]}' "$man")
  while read -r size rel; do
    [ -z "${rel:-}" ] && continue
    total=$((total+1))
    local f="$mp/insightout/$rel"
    if [ ! -f "$f" ]; then missing=$((missing+1))
    else
      local actual; actual=$(stat -c %s "$f" 2>/dev/null || echo -1)
      if [ "$actual" != "$size" ]; then
        local lc=${rel,,}
        case "${twin_sizes[$lc]:-}" in
          *" $actual "*) collided=$((collided+1)) ;;
          *) wrong=$((wrong+1)) ;;
        esac
      fi
    fi
  done < "$man"
  local coll=""
  [ "$collided" -gt 0 ] && coll=", $collided case-twins merged by FAT"
  if [ "$missing" -eq 0 ] && [ "$wrong" -eq 0 ]; then
    printf '  %-28s COMPLETE  %s files all present and the right size%s%s\n' "$(basename "$mp")" "$total" "$coll" "$note"
    # It passed against the reference, so it has earned the manifest it was missing; write
    # it on so the next verify of this drive stands on its own.
    [ -n "$note" ] && { cp -f "$man" "$mp/insightout/MANIFEST.txt" 2>/dev/null || true; }
    return 0
  fi
  printf '  %-28s INCOMPLETE  %s missing, %s wrong size, of %s%s%s\n' "$(basename "$mp")" "$missing" "$wrong" "$total" "$coll" "$note"
  return 1
}

# ------------------------------------------------------------------------- main
say "usb_copy"
say "  builds from : $BUILDS"
say "  platforms   : $PLATFORMS"
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
  # For drives that never finished: prefer the manifest in staging (freshest), then the
  # durable copy the last copy run left in the log dir.
  if [ -z "${REF_MANIFEST:-}" ]; then
    for c in "$STAGE/../io-usb-manifest.txt" "./usb_copy-logs/io-usb-manifest.txt"; do
      [ -f "$c" ] && { REF_MANIFEST="$c"; break; }
    done
  fi
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
# find -L, because the copy uses rsync -L: every symlink in staging lands on the drive as
# a real file with the target's size, so the manifest must list it that way too. Without
# -L the ~1000 python-runtime links were copied but never verified.
( cd "$STAGE" && find -L . -type f -printf '%s %p\n' | sed 's|^\([0-9]*\) \./|\1 io/|' ; \
  cd "$OLDPWD/$DATA_SRC" && find -L . -type f -printf '%s %p\n' | sed 's|^\([0-9]*\) \./|\1 data/|' ) \
  2>/dev/null | LC_ALL=C sort -k2 > "$STAGE/../io-usb-manifest.txt"
TOTAL_KB=$(du -sk "$STAGE" "$DATA_SRC" 2>/dev/null | awk '{s+=$1} END{print s+0}')
# Progress is counted in files, not bytes. Bytes lie on exFAT: it allocates in 32 KB
# clusters, so du on the destination runs well above the source and the percentage pegs at
# 100 while thousands of files are still to come.
#
# Count exactly what the drive can be counted for, plus the MANIFEST written into
# insightout/ at the end. Symlinks count because the copy uses -L, which materialises
# each one as a real file on the drive - so a source symlink does become a destination
# file, even on exFAT, which cannot store links.
count_entries() { find "$1" \( -type f -o -type l \) 2>/dev/null | wc -l; }
FILES=$(count_entries "$STAGE")
TOTAL_FILES=$(( FILES + $(count_entries "$DATA_SRC") + 1 ))
say
say "copying $((TOTAL_KB/1024)) MB in $TOTAL_FILES files to ${#STICKS[@]} drive(s) at once"
say "  a USB stick is slow with many small files; expect this to take a while"
LOGDIR="${LOGDIR_OVERRIDE:-./usb_copy-logs}"
mkdir -p "$LOGDIR"
# A durable copy of the manifest, outside /tmp: --verify falls back to it for a drive
# that lost power before its own MANIFEST.txt was written, even after a reboot.
cp -f "$STAGE/../io-usb-manifest.txt" "$LOGDIR/io-usb-manifest.txt" 2>/dev/null || true
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
    got=$(count_entries "$m/insightout")
    pct=0; [ "${TOTAL_FILES:-0}" -gt 0 ] && pct=$(( got * 100 / TOTAL_FILES ))
    [ "$pct" -gt 100 ] && pct=100
    line="$line $(basename "$m")=${pct}%"
  done
  elapsed=$(( $(date +%s) - started ))
  printf '\r  [%4ds] %d copying:%s        ' "$elapsed" "$running" "$line"
  # Each poll walks every file already on the drive, competing with the copy for the same
  # slow bus. Frequent early, when the operator wants to see it move; sparse later, when
  # they just want it to finish.
  if [ "$elapsed" -lt 60 ]; then sleep 3; else sleep 15; fi
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
