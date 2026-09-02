# Putting a release on a USB drive

For running an event with many drives at once:
[EVENTS.md](EVENTS.md).

You need about 9 GB free on your machine (3.2 GB of archives, 5.6 GB unpacked) and a
16 GB drive. Plug the drive in and check it is mounted before you start:

```bash
lsblk -o NAME,LABEL,SIZE,TRAN,MOUNTPOINT | grep media
```
Then run

```bash
cd ~/src/github.com/bprashanth/io          # the repo root - every path below is relative to it

# 1. clear any previous release.
rm -rf /media/$USER/*/insightout /media/$USER/*/START-HERE.txt
rm -rf "${TMPDIR:-/tmp}"/io-usb-stage*

# 2. fetch the new release  (3.2 GB)
rm -rf bin && mkdir bin
gh release download v0.3.2 -R bprashanth/io -D bin

# 3. check the download is not truncated, before spending an hour copying it
cd bin && sha256sum -c SHA256SUMS.txt && cd ..

# 4. copy to the drive
./app/io/usb_copy.sh --dry-run             # names the drive it found, writes nothing
./app/io/usb_copy.sh

# 5. prove the drive is complete - this is the only thing that counts as done
./app/io/usb_copy.sh --verify

# 6. reclaim the space (optional; --verify still works after this)
rm -rf "${TMPDIR:-/tmp}"/io-usb-stage* bin
```

**Only need one platform?** A third of the size, a third of the files, most of the time
saved. Use the same platform in both commands:

```bash
gh release download v0.3.2 -R bprashanth/io -D bin -p 'io-win-*' -p 'SHA256SUMS.txt'
./app/io/usb_copy.sh --platform win        # win | mac | linux, or win,linux
```

Notes:

- `--verify` must say `COMPLETE`. If it says `INCOMPLETE`, run `./app/io/usb_copy.sh` again -
  it repairs what is missing and skips the rest.
- Re-downloading into a `bin/` that still has files fails with `already exists`. That is why
  step 2 removes it. There is no resume: an interrupted download must be fetched again.
- Deleting `bin/` means another 3.2 GB download before you can prepare another drive.
- The copy takes a while - about 45,000 small files, which a USB stick writes slowly. If it
  looks stuck, [EVENTS.md](EVENTS.md#when-the-copy-looks-stuck) has the diagnosis order.

**If the drive is damaged** (I/O errors, or an interrupted copy), reformat it. Check the
device name against `lsblk` first - `/dev/sda1` is the internal disk on many machines:

```bash
udisksctl unmount -b /dev/sdb1
sudo mkfs.exfat -L DIGITEK /dev/sdb1       # -L keeps the name; older tools use -n
```

Then unplug and replug it, or `usb_copy` will not see it.

## Starting io from the drive

Everything is on the drive. 

**Windows**

1. Open `insightout\io\io-win-x64-offline`
2. Copy that whole folder to your computer - the Desktop is fine. It runs from the drive
   too, but everything is slower.
3. Double-click `io.exe`
4. Windows shows a blue "Windows protected your PC" box. Click **More info**, then
   **Run anyway**. It says that because the app is not signed by a publisher Microsoft
   recognises.

**Mac, Apple silicon (M1-M4)**

1. Double-click `insightout/io/io-mac-arm64-offline.dmg`
2. Drag `io` out to your Desktop or home folder - **not** into Applications
3. **Right-click `io` and choose Open**, then Open again. A plain double-click is blocked
   the first time. Normal double-clicks work after that.

**Mac, Intel**

Same as above, with `insightout/io/io-mac-x64.dmg`. Two differences: the first start needs
internet and takes a few minutes, and io will say the private-data scanner cannot run on an
Intel Mac. That is expected - ask the organizers for a privacy server address.

**Linux**

1. Copy `insightout/io/io-linux-x64-offline` to your home folder
2. Run `./io` in a terminal from inside it. Or right-click `io` → Properties → Permissions →
   tick "Allow executing file as program", then double-click.

Once io opens it asks for an API key or a server address, shows a short note about your
data, and is ready for a folder. There is sample data on the drive at `insightout/data`.
