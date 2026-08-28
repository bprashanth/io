# Antigravity on Linux

Install Antigravity first. The plugin is pinned to Antigravity **1.107.0**
(`antigravity --version`; that's the build version, which is released as 1.23.2
[here](https://antigravity.google/releases) ).

*Debian/Ubuntu x86 (apt):*

**IMPORTANT**:  `sudo apt purge antigravity` first if the output of `antigravity --version` is not `1.107.0`. 
```
sudo install -m 0755 -d /etc/apt/keyrings
curl -s https://us-central1-apt.pkg.dev/doc/repo-signing-key.gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/antigravity-repo-key.gpg
echo "deb [signed-by=/etc/apt/keyrings/antigravity-repo-key.gpg] https://us-central1-apt.pkg.dev/projects/antigravity-auto-updater-dev/ antigravity-debian main" \
  | sudo tee /etc/apt/sources.list.d/antigravity.list
sudo apt update && sudo apt install -y antigravity=1.23.2-1776332190
sudo apt-mark hold antigravity     # pin until after the event
antigravity --version              # must print 1.107.0
```

*No-apt / ARM fallback (tarball):* download
[x86](https://edgedl.me.gvt1.com/edgedl/release2/j0qc3/antigravity/stable/1.23.2-4781536860569600/linux-x64/Antigravity.tar.gz)
or
[ARM](https://edgedl.me.gvt1.com/edgedl/release2/j0qc3/antigravity/stable/1.23.2-4781536860569600/linux-arm/Antigravity.tar.gz),
then:


**NOTE**: you only need this OR the apt install above, NOT both.  
```
cd ~/Downloads                      # or wherever the tarball is
tar -xvzf Antigravity*.tar.gz       # filename case varies
sudo rm -rf /opt/antigravity        # nuke any old copy
sudo mv Antigravity /opt/antigravity   # the extracted app dir (holds bin/, resources/)
sudo ln -sf /opt/antigravity/bin/antigravity /usr/local/bin/antigravity
antigravity --version               # must print 1.107.0
```

**NOTE**: if you want to turn off permission requests for the term of this session, you can find the setting that say "Auto Execute" and "Review Policy" and set them to "Always Proceed". You can always turn this back to "Request Review" later. These settings are found in the bottom right corner of antigravity.

## Then

Install the privacy shield: back to the [README](../README.md#a-the-privacy-shield-in-antigravity).
