# Getting io onto laptops, and running the event

Everything an organizer does, in order. Start to finish this is a repo checkout, a set of
USB drives, and two servers on the day.

## 1. Get the builds

Built by `.github/workflows/package.yml`, one run per flavour:

```
gh workflow run package.yml --ref main -f fat=false     # thin, all platforms
gh workflow run package.yml --ref main -f fat=true      # offline, all platforms
gh workflow run package.yml --ref main -f only=mac      # just one platform
gh workflow run package.yml --ref main -f fat=true -f release_tag=v0.3.0   # publish as well
```

`release_tag` makes each runner upload straight to that release, which is much faster than
pulling several gigabytes down and pushing them back.

Then put the archives in `bin/` at the root of the repo:

```
gh release download v0.3.0 --dir bin
```

### What exists, and what does not

| platform | offline (no download) | thin (downloads on first start) |
|---|---|---|
| Windows | `io-win-x64-offline.zip` | `io-win-x64.zip` |
| Linux | `io-linux-x64-offline.tar.gz` | `io-linux-x64.tar.gz` |
| macOS Apple Silicon | `io-mac-arm64-offline.dmg` | `io-mac-arm64.dmg` |
| macOS Intel | **none, and none is possible** | `io-mac-x64.dmg` |

There is no Intel Mac offline build because there is nothing to put in it: PyTorch has
shipped no macOS x86_64 wheel since 2.2.2, and the rest of the stack needs a newer torch
than that. An Intel Mac runs io without the local scanner and is offered a privacy server
instead. There is no `.AppImage` either; it needed a library recent Ubuntu does not ship
and could not start without an administrator password.

## 2. Put it on the drives

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

About 6.3 GB and 77,861 files per drive. On exFAT `du` reports around 7.5 GB, because it
allocates in 32 KB clusters and most of those files are small. **Budget 16 GB drives.**

Expect it to take a while and do not read that as a hang: the Windows offline pack alone is
37,306 files, and a stick writes many small files far more slowly than its rated speed. The
script prints a per-drive percentage counted in files.

### Verifying, and repairing

`--verify` compares every file against `MANIFEST.txt` and reports COMPLETE or INCOMPLETE.
Re-running the copy repairs whatever is missing or the wrong size, and skips the rest.

If a drive was interrupted mid-copy its filesystem may be damaged. `fsck.exfat` will say
so. Reformat rather than repair, since the contents are about to be overwritten anyway:

```
sudo umount /dev/sdX1 && sudo mkfs.exfat -n "LABEL" /dev/sdX1
```

Then unplug and replug it so it mounts, or `usb_copy` will not see it.

### Which drives can be run from directly

- **Windows: yes.** The zip has no symlinks and Windows has no executable bit.
- **Linux: yes**, but copy it off first for speed. exFAT cannot store symlinks, so the app
  finds its interpreter by versioned name instead.
- **macOS: no.** A `.app` bundle is held together by symlinks, which exFAT cannot store.
  The `.dmg` sits on the drive fine; copy the app out of it onto the Mac.

## 3. On the day

```
./installation/scripts/event_start.sh
```

Starts both servers and prints the addresses to read out. `--stop` stops them, `--board-only`
and `--scanner-only` start one, and `BOARD_PORT` / `SCANNER_PORT` move them if a port is busy.
It says a server has started only once that server actually answers on its port, and it exits
on its own if both servers stop, so the window is never claiming to run something that is not.

- **room board**, default 8890. Put it on the projector; it refreshes itself every three
  seconds and shows what the room preferred. Votes append to `app/io/room-votes.jsonl`, and
  `GET /votes.jsonl` hands the whole log back afterwards.
- **privacy server**, default 8899. Only for laptops that cannot run the scanner themselves.

Everyone must be on the same wifi as that machine, and the first start may raise a firewall
prompt to allow incoming connections.

### The privacy server, and what it costs

Text sent to it is **not redacted**. It cannot be: finding the private values in it is the
job. So a laptop using it sends real names and numbers across the room's network to the
organizer's machine. io asks the person before it ever does this, and names the server.

Give that address only to people whose io tells them the scanner cannot run. Everyone else
scans on their own machine and nothing leaves it. The alternative, if someone would rather
not, is pattern matching only: it still finds phone numbers, Aadhaar and account numbers and
emails, but not people's names or place names in free text.

## 4. What each participant does

`START-HERE.txt` on the drive covers it, one section per computer. In short: copy the folder
for their machine, run it, and dismiss one security prompt, because io is not signed.

- Windows: SmartScreen, More info, Run anyway
- macOS: right-click, Open, Open. A plain double-click is blocked the first time
- Linux: allow the file to run as a program, or `./io` in a terminal

Then io asks for an API key or a server address, shows a short note about data, and is ready
for a folder. There is sample data at `insightout/data`.

## 5. If someone cannot install it

In order:

1. **The offline build** from the drive. Downloads nothing.
2. **A privacy server address**, if io says the scanner cannot run on their computer.
3. **Pattern matching only**, if they would rather not use a server.
4. **From source**, if a download will not start at all:
   [running io from source](INSTALL-from-source.md). Needs python 3.10+ and node 18+.

## Where the details live

- [Windows](INSTALL-windows.md), [macOS](INSTALL-mac.md), [Linux](INSTALL-linux.md)
- [Antigravity, per platform](ANTIGRAVITY-linux.md) and [what to pick on first run](ANTIGRAVITY-first-run.md)
- [Running io from source](INSTALL-from-source.md)
- `app/io/README.md` for what each script in that folder does
