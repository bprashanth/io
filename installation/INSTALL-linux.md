# Installing io on Linux

You do not need Python. You do not need Node. You do not need an admin password.

Download from [the releases page](https://github.com/bprashanth/io/releases/latest).

## Which file to take

Take the **tar.gz**. It works on every distribution.

| your machine | file |
|---|---|
| a normal laptop (Intel or AMD) | `io-linux-x64.tar.gz` |
| an ARM laptop | `io-linux-arm64.tar.gz` |

Not sure which you have? Run `uname -m`. If it says `x86_64` take the x64 file. If it
says `aarch64` take the arm64 one.

There is also an `.AppImage`. Skip it unless you already know you want it. See the note at
the bottom for why.

## Install

Unpack it and start it. Two commands.

```
tar -xzf io-linux-x64.tar.gz
./io-linux-x64/io
```

To start it from your file manager instead of the terminal: open the `io-linux-x64`
folder, right-click the file called `io`, choose Properties, then Permissions, then tick
"Allow executing file as program". Now you can double-click it.

## The first start takes a few minutes

The first time you run io it sets itself up. It shows a small window that tells you what
it is doing:

- getting a self-contained python (about 46 to 110 MB, depending on your machine)
- installing what it needs to read your files (about 1.2 GB on disk)
- getting the on-device scanner that finds names and numbers (about 500 MB)

A clock in that window counts up so you can see it is still working. On a normal laptop
this takes **one to two minutes**. On an older machine, or slow wifi, it can take longer.

It needs internet this one time. After that io works offline.

If you want to watch it in detail, open another terminal:

```
tail -f ~/.local/share/io/install.log
```

When it finishes, io asks for an API key or a server address. Ask the organizers for
this. It is kept in memory only, so io asks again next time you start it.

**Every start after the first one takes about a second.** Nothing is downloaded again.

## If something goes wrong

Everything io installed is in one folder, and it is safe to delete:

```
rm -rf ~/.local/share/io
```

Start io again and it will set itself up from scratch. This is also how you test a fresh
install on purpose.

Your folder list, your corrections and your vault are somewhere else:

```
~/.config/io
```

Delete that only if you want io to forget which folders you added and how you corrected
the scanner.

If the setup stops with an error, it tells you where the log is. The log is
`~/.local/share/io/install.log`, and the last few lines say what it was doing. A dropped
connection is the common one. Starting io again picks up where it left off.

## Why not the AppImage

An AppImage is one file you double-click, which is nicer. But it needs a system library
called libfuse2, and Ubuntu 24.04 and later no longer install it. On those machines a
double-click fails with:

```
dlopen(): error loading libfuse.so.2
AppImages require FUSE to run.
```

The fix for that is `sudo apt install libfuse2t64`, which needs an admin password. The
tar.gz needs nothing, so that is the one we point people at.

If you do want to run the AppImage without installing anything, this works:

```
chmod +x io-linux-x86_64.AppImage
APPIMAGE_EXTRACT_AND_RUN=1 ./io-linux-x86_64.AppImage
```

## If it will not start

Two fallbacks, in order:

1. Ask the organizers for the USB stick. It has a version with everything already inside
   it: it downloads nothing and starts in seconds.
2. Build it from this repository instead:
   [running io from source](INSTALL-from-source.md). Needs python 3.10+ and node 18+.

## The offline build

For events without reliable wifi there is a second, much larger file with everything
already inside it. It does no downloading at all and reaches the provider screen in a
couple of seconds. Ask the organizers for it if you need it.
