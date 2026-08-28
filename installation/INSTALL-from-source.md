# Running io from the source code

This is the fallback. If a downloaded build will not start on your machine, this path
builds io from the repository instead, and it works on Linux, macOS and Windows.

It needs two things already installed, which the downloaded builds do not:

- **python 3.10 or newer** - check with `python3 --version`
- **node 18 or newer** - check with `node --version`

If you do not have those, and cannot install them, use a packaged build instead:
[Linux](INSTALL-linux.md).

## Linux and macOS

```
git clone https://github.com/bprashanth/io.git
cd io/app/io
./install.sh
./run.sh
```

## Windows

Open PowerShell in the same folder and run the steps by hand. `install.ps1` is not
maintained; the packaged Windows build is the supported path and needs nothing installed.

```
git clone https://github.com/bprashanth/io.git
cd io\app\io
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.13.0
.\.venv\Scripts\python.exe -m pip install gliner==0.2.28 transformers==5.13.1 huggingface_hub==1.28.0 numpy==2.5.2 pandas==3.0.5 openpyxl==3.1.5 pypdf==6.16.2
$env:HF_HOME = "$PWD\hf-cache"
.\.venv\Scripts\python.exe -c "from gliner import GLiNER; GLiNER.from_pretrained('knowledgator/gliner-pii-edge-v1.0', map_location='cpu')"
npm install
npm start
```

## What the install does

One time, about 1.9 GB on disk, internet needed once:

1. makes a python environment in `app/io/.venv`
2. installs the pinned packages - the versions come from `app/io/pins.json`, the same file
   the downloaded builds use, so a checkout runs identical code
3. downloads the on-device scanner into `app/io/hf-cache` (about 500 MB)
4. installs Electron

Expect one to three minutes on a normal machine. After that `./run.sh` starts io in about
a second, and nothing is downloaded again.

## Where it keeps things

A checkout install is not portable: it keeps the environment beside the code
(`app/io/.venv`, `app/io/hf-cache`) and its settings, folder list and vault in
`~/.config/io`.

To start over, delete `app/io/.venv` and `app/io/hf-cache` and run `./install.sh` again.
To make io forget which folders you added and how you corrected the scanner, delete
`~/.config/io`.

## If it fails

`./install.sh` stops at the first problem and prints what it was doing. The usual ones:

- **"python 3.10+ is required"** - your `python3` is older. Install a newer one, or point
  the script at one you have: `PYTHON=/path/to/python3.12 ./install.sh`.
- **"node 18+ is required"** - install node, or use a packaged build instead.
- **a download failed partway** - run `./install.sh` again; it picks up where it stopped.

If io starts but the window stays empty, the service log is at `~/.config/io/io.log` for a
checkout install, and its last lines say what went wrong.
