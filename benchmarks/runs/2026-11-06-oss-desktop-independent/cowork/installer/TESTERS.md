# Installing Idli (testers)

You need: the installer for your computer, and your **Idli code** (one line starting `idli1.`, sent to you
privately). Idli isn't signed yet, so your computer warns once; the steps below get past it.

## Windows (10 or 11, 64-bit)
1. Run `Idli-Setup-<version>.exe`.
2. Windows says "Windows protected your PC": click **More info**, then **Run anyway**.
3. Click through the installer (no admin needed). Leave "Open Idli" ticked and finish.

## Mac (Apple silicon: M1 or newer)
1. Open `Idli-<version>-arm64.dmg` and drag **Idli** onto **Applications**.
2. Open Idli from Applications. macOS says it can't check it for malware: click **Done** (or Cancel).
3. Open **System Settings > Privacy & Security**, scroll down to "Idli was blocked", click **Open Anyway**, and
   confirm with your password. (On macOS 14 or older: right-click Idli > Open > Open.)

## Linux (Ubuntu 22.04+ / Pop!_OS, 64-bit Intel/AMD)
1. Double-click `idli_<version>_amd64.deb` and click Install, or run `sudo apt install ./idli_<version>_amd64.deb`.
2. Open **Idli** from your apps.

## First time you open it
A setup page opens in your browser:
1. **Connect to Idli's model**: paste your Idli code, click Connect.
2. **Connect Claude (optional)**: Install, then Sign in (your own Anthropic account). Skip it if you like: Idli
   still finds and checks files and answers questions about files it already knows; only teaching it a new kind
   of file needs Claude.
3. Click **Open Idli**. Idli (built on Paseo) opens; in **Start here**, sign in to Google in the Drive tab and say
   yes to indexing.

To change the code or connect Claude later, open **Idli setup** (Start menu / apps; on Mac run
`Idli setup.command` from the disk image). Logs: `idli-insights/config/idli-app.log` in your home folder.
