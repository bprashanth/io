# Getting io onto laptops, and running the event

Organizer flow on the day of the event. 

## 1. Get the builds [Pre-Event]

Built by `.github/workflows/package.yml`, one run per flavour:

```
gh workflow run package.yml --ref main -f fat=false     # thin, all platforms
gh workflow run package.yml --ref main -f fat=true      # offline, all platforms
gh workflow run package.yml --ref main -f only=mac      # just one platform
gh workflow run package.yml --ref main -f fat=true -f release_tag=v0.3.1   # publish as well
```

`release_tag` makes each runner upload straight to that release, which is much faster than
pulling several gigabytes down and pushing them back.

Then put the archives in `bin/` at the root of the repo:

```
gh release download v0.3.1 --dir bin
```

(insert the latest release number if it's not `0.3.1` by checking this repo's releases page). 

__What this contains__

| platform | offline (no download) | thin (downloads on first start) |
|---|---|---|
| Windows | `io-win-x64-offline.zip` | `io-win-x64.zip` |
| Linux | `io-linux-x64-offline.tar.gz` | `io-linux-x64.tar.gz` |
| macOS Apple Silicon | `io-mac-arm64-offline.dmg` | `io-mac-arm64.dmg` |
| macOS Intel | **none, and none is possible** | `io-mac-x64.dmg` |

There is no Intel Mac offline build (not possible because currently supported
pytorch libraries don't support mac-intel). So mac intel users are confined to
the online only flow - meaning the gliner server must run on a non-mac-intel
machine. 

## 2. Put it on the drives [Pre-Event]

Plug in as many drives as you like and run, from the root of the repo:

```
./app/io/usb_copy.sh --dry-run     # list the drives it found, write nothing
./app/io/usb_copy.sh               # copy to all of them at once
./app/io/usb_copy.sh --verify      # prove each drive is complete
```

Each drive gets:

```
START-HERE.txt              what a participant does, one section per computer
insightout/io/              the unpacked builds, .dmg carried as-is
insightout/data/            sample data to try
insightout/MANIFEST.txt     every file and its size, for --verify
```

**Budget 16 GB drives.**
About 6.3 GB and 77,861 files per drive. 

Expect it to take a while and do not read that as a hang: the Windows offline pack alone is
37,306 files, and a stick writes many small files far more slowly than its rated speed. The
script prints a per-drive percentage counted in files.

__Verifying, and repairing__

Running `usb_copy.sh --verify` compares every file against `MANIFEST.txt` and reports COMPLETE or INCOMPLETE.
Re-running the copy repairs whatever is missing or the wrong size, and skips the rest.

If a drive was interrupted mid-copy its filesystem may be damaged. `fsck.exfat` will say
so. Reformat rather than repair, since the contents are about to be overwritten anyway:

```
sudo umount /dev/sdX1 && sudo mkfs.exfat -n "LABEL" /dev/sdX1
```

Then unplug and replug it so it mounts, or `usb_copy` will not see it.

## At the event 

1. Organizer setup
2. Participant setup (usb)
3. Participant acttions (outside-in) 
4. If someone cannot install something 

## 1. Orgranizer Team

```
./installation/scripts/event_start.sh
```

Starts two servers and prints the addresses to read out. `--stop` stops them, `--board-only`
and `--scanner-only` start one, and `BOARD_PORT` / `SCANNER_PORT` move them if a port is busy.
It says a server has started only once that server actually answers on its port, and it exits
on its own if both servers stop.

- **room board**, default 8890. Put it on the projector; it refreshes itself every three
  seconds and shows what the room preferred. Votes append to `app/io/room-votes.jsonl`, and
  `GET /votes.jsonl` hands the whole log back afterwards.
- **privacy server**, default 8899. Only for laptops that cannot run the scanner themselves.

Everyone must be on the same wifi as that machine, and the first start may raise a firewall
prompt to allow incoming connections.

## 2. Participatn setup (usb) 

Plug the drive into each laptop and do the following: 

__Windows__

1. Open `insightout\io\io-win-x64-offline`
2. Copy that whole folder to their computer (desktop is fine). 
    - IFF they don't have space, tell them to wait while you copy it to other computers, then give them the usb (they can run it directly from the usb). 
3. Double click the exe. Windows smartscreen will show a warning, click "Run Anyway". 

__MacOS: Silicon__

1. Double click `insightout/io/io-mac-arm64-offline.dmg`
2. Drag `io` out of the dmg onto their Desktop or home folder (DO NOT DRAG IT INTO APPLICATIONS OR THE APP TRAY)
3. Right-click `io` -> open -> open again. A plain double-click will be blocked the first time. 

__MacOS: Intel__

Same as above, but for `io-mac-x64.dmg`. It will say the scanner can't run on an Intel Mac. This is expected, you will hav to use the local address of the privacy-server you started on your laptop (see previous section).

__Linux__

1. Copy `insightout/io/io-linux-x64-offline` to their home dir 
2. `./io` in a terminal, or right click -> Properties -> Permissions -> "Allow executing file as program" 

## 3. Participatn Actions 

Starting io asks for an API key or a server address, shows a short note about data, and is ready
for a folder. There is sample data at `insightout/data`.

## 4. If someone cannot install something 

In order:

1. **The offline build** from the drive. Downloads nothing.
2. **A privacy server address**, if io says the scanner cannot run on their computer.
3. **Pattern matching only**, if they would rather not use a server.
4. **From source**, if a download will not start at all:
   [running io from source](INSTALL-from-source.md). Needs python 3.10+ and node 18+.

## When the copy looks stuck

Copying ~3.5 GB of ~80,000 small files to eight sticks at once is slow, and almost every
"it has hung" turns out to be either real work or a number that is lying. Diagnose in
this order.

**1. Read the rsync logs, not the drives.** This is the only signal that costs the drives
nothing, and it is rsync's own counter rather than anything the script computes:

```bash
for f in usb_copy-logs/*.log; do
  printf '%-22s %s\n' "$(basename "$f" .log | sed 's/.*_//')" \
    "$(tr '\r' '\n' < "$f" | grep -oE 'xfr#[0-9]+, to-chk=[0-9]+/[0-9]+' | tail -1)"
done
```

Run it twice, sixty seconds apart. `to-chk` falling or `xfr#` rising means it is working.
`to-chk` is the position in the walk through the whole list; `xfr#` is files actually
written, and it stays low on a drive that is mostly already correct, because rsync skips
what matches. `to-chk`'s total counts directories too, so it is larger than the file-only
percentage the script prints. The two numbers disagreeing is normal.

**2. Ask what the processes are doing.**

```bash
ps -eo pid,stat,etimes,wchan:20,args --sort=-etimes | grep -E 'rsync|cp |usb_copy' | grep -v grep
```

`STAT` of `D` is blocked on disk I/O, which is the normal state for a USB stick. **A `cp -r`
in this list means a bug has returned** - see below.

**3. Only then conclude it is stuck.** Ctrl-C is safe: rsync removes its in-flight temp
file on SIGINT, so a drive is left holding complete files and nothing half-written. Re-run
to resume; it skips what is already correct.

### Things that were wrong here before, and what they looked like

Each of these presented as "the copy has hung". They are fixed, but knowing the shape of
them makes a relapse obvious.

- **rsync fails on exFAT and a fallback re-copies everything.** The packs carry ~1,000
  symlinks inside the bundled python runtime, and exFAT cannot store a symlink. Plain
  `rsync -a` therefore exits 23, and the old code read any non-zero exit as "rsync is
  unusable" and re-copied all 3.5 GB with `cp -r`, on every drive, on every run, *after*
  rsync had already finished. Runs never ended, and `MANIFEST.txt` - written last - was
  never reached, so `--verify` could only report NO MANIFEST. Fixed by `rsync -a -L`,
  which sends the file a symlink points at. To check the fix is present on a real stick,
  no root needed:

  ```bash
  mkdir -p /tmp/lt && echo hi > /tmp/lt/a && ln -s a /tmp/lt/l
  M=/media/$USER/SOMESTICK
  rsync -a    /tmp/lt/ "$M/_probe/"; echo "plain -a exit=$?"   # 23 on exFAT
  rm -rf "$M/_probe"
  rsync -a -L /tmp/lt/ "$M/_probe/"; echo "with -L  exit=$?"   # 0
  rm -rf "$M/_probe"
  ```

- **Progress measured in bytes.** exFAT allocates in 32 KB clusters, so the destination
  reads larger than the source and the percentage pegs at 100 with thousands of files
  still to come. It counts files now.

- **Progress counting things the drive cannot hold.** Counting symlinks in the total made
  a finished copy read 98% forever, because exFAT never stores them. Whatever the
  denominator counts must be what actually lands - with `-L`, a source symlink does become
  a destination file, so it counts again.

- **`du` on the destination.** Walking ~75,000 files back off a stick, on eight drives at
  once, took longer than parts of the copy it was reporting on. Do not add one; use the
  manifest or the logs.

- **A bare `sync`.** It flushes every filesystem on the machine, so all eight copies waited
  for the slowest drive after their own data was safely down. `sync -f` waits for one.

- **Staging thrown away every run.** Staging is unpacked once and reused, and validates
  itself by counting files *and symlinks* against the archive listing. When it counted only
  regular files, any archive holding a symlink never matched, so every run deleted and
  re-extracted gigabytes before copying anything. If you see `re-unpacking` on every run
  rather than `already unpacked`, that check is broken again.

### Testing a change to usb_copy.sh

**A directory on the normal filesystem is not a valid test target.** `rsync -a` exits 0
there and hides the entire class of bug above. Test against a real stick, or against a
FAT image if you have root:

```bash
dd if=/dev/zero of=/tmp/t.img bs=1M count=600 && mkfs.vfat -F 32 /tmp/t.img
mkdir -p /tmp/tmnt && sudo mount -o loop,uid=$(id -u),gid=$(id -g) /tmp/t.img /tmp/tmnt
./app/io/usb_copy.sh --builds ./bin --target /tmp/tmnt
./app/io/usb_copy.sh --builds ./bin --target /tmp/tmnt --verify
```

### A drive whose filesystem is damaged

An interrupted copy can corrupt exFAT. Needs root, so if sudo prompts, ask rather than
working around it.

```bash
sudo fsck.exfat -n /dev/sdXN          # inspect, changes nothing
sudo umount /dev/sdXN
sudo mkfs.exfat -n IONAME /dev/sdXN   # reformat, then re-run usb_copy
```

## More info

- [Windows](INSTALL-windows.md), [macOS](INSTALL-mac.md), [Linux](INSTALL-linux.md)
- [Antigravity, per platform](ANTIGRAVITY-linux.md) and [what to pick on first run](ANTIGRAVITY-first-run.md)
- [Running io from source](INSTALL-from-source.md)
- `app/io/README.md` for what each script in that folder does
