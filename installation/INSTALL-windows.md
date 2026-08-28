# io on Windows

You do not need Python. You do not need Node. You never need an administrator password.

1. Download **io-win-x64.zip** from [the releases page](https://github.com/bprashanth/io/releases/latest).
2. Right-click it, Extract All. Extract to somewhere short like `C:\io`.
3. Open the folder and double-click **io.exe**.

## The one prompt you will see

Windows shows a blue box saying it protected your PC. That is because io is not signed by
a company Microsoft recognises, not because anything is wrong.

Click **More info**, then **Run anyway**.

You only see this the first time.

## The first start takes a few minutes

io sets itself up: it gets a self-contained python, what it needs to read your files, and
the on-device scanner that finds names and numbers. A small window shows what it is doing,
with a clock counting up.

Two to three minutes is normal. Windows Defender reads every file as it is written, so an
older laptop can sit here longer. It needs internet this one time. After that io works
offline, and every later start takes about a second.

## If it will not start

Ask the organizers for the USB stick. It has a version with everything already inside it:
copy the folder off the stick, double-click io.exe, and it starts in seconds without
downloading anything.

## Starting over

Delete this folder:

    %LOCALAPPDATA%\io

Paste that into the address bar of any folder window. Start io again and it sets itself up
from scratch. Your folder list and corrections live in `%USERPROFILE%\.config\io`;
delete that only if you want io to forget them.
