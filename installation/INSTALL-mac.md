# io on macOS

You do not need Python. You do not need Node. You never need an administrator password.

1. Download from [the releases page](https://github.com/bprashanth/io/releases/latest).
   Which one depends on your Mac. Apple menu, About This Mac: an M1/M2/M3/M4 is Apple
   Silicon, anything saying Intel is Intel.
   - Apple Silicon: **io-mac-arm64-offline.dmg**
   - Intel: **io-mac-x64-offline.dmg**
   These offline files download nothing. The smaller files are **io-mac-arm64.dmg**
   and **io-mac-x64.dmg**. They download about 1.9 GB on first start.
2. Double-click the .dmg, then drag **io** into Applications.

## The one prompt you will see

The first time, a plain double-click will be blocked. macOS says io cannot be opened
because the developer cannot be verified. That is because io is not signed with an Apple
account, not because anything is wrong.

**Right-click** io, choose **Open**, then **Open** again in the box that appears.

You only need to do this once. After that a normal double-click works.

## The first start

If you took an offline file, there is no wait. It downloads nothing and opens in a few
seconds, the first time and every time.

If you took a smaller file, the first start takes a few minutes. io sets itself up: it gets
a self-contained python, what it needs to read your files, and the on-device scanner that
finds names and numbers. A small window shows what it is doing, with a clock counting up.
One to two minutes is normal, and it needs internet this one time. After that io works
offline, and every later start takes about a second.

## If it will not start

Ask the organizers for the USB stick. It has a version with everything already inside it:
copy it off the stick, open it, and it starts in seconds without downloading anything.

## Starting over

Delete this folder:

    ~/Library/Application Support/io

In Finder, use Go, Go to Folder, and paste that. Start io again and it sets itself up from
scratch. Your folder list and corrections live in `~/.config/io`; delete that only if you
want io to forget them.
