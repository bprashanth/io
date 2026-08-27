// One config, three platforms, two flavours.
//
//   npm run pack                     thin artifact for the host platform
//   IO_FAT=1 IO_PAYLOAD=… npm run pack   the same app with runtime/ and hf-cache/ baked in
//
// The fat payload is whatever `node bootstrap.js --dest <dir>` produced on a machine of the
// target OS and architecture. It has to be built on the target: the wheels inside it are
// compiled, so a payload made on Linux is useless to a Windows participant.

const path = require('path');
const fs = require('fs');

const FAT = process.env.IO_FAT === '1';
const PAYLOAD = path.resolve(process.env.IO_PAYLOAD || path.join(__dirname, 'payload'));

// The python side has to be real files on disk: service.py resolves its engine and ui
// folders from __file__, and nothing can import out of an asar. So the Electron shell is
// asar'd and everything python lives beside it under resources/io/.
const extraResources = [
  { from: 'service.py', to: 'io/service.py' },
  { from: 'engine', to: 'io/engine', filter: ['**/*.py'] },
  { from: 'ui', to: 'io/ui' },
];

if (FAT) {
  for (const part of ['runtime', 'hf-cache']) {
    const src = path.join(PAYLOAD, part);
    if (!fs.existsSync(src)) {
      throw new Error(`IO_FAT=1 but ${src} is missing. Run: node bootstrap.js --dest ${PAYLOAD}`);
    }
    extraResources.push({ from: src, to: part });
  }
}

const suffix = FAT ? '-offline' : '';

module.exports = {
  appId: 'org.insightout.io',
  productName: 'io',
  copyright: 'io',
  directories: { output: 'dist', buildResources: 'icons' },
  asar: true,
  files: [
    'main.js', 'preload.js', 'runtime.js', 'bootstrap.js', 'pins.json', 'splash.html',
    'icons/icon.png',
  ],
  extraResources,

  win: {
    // A zip of a portable folder, not an installer: nothing to elevate, nothing to
    // uninstall, and it runs from a USB stick. Unsigned, so first launch shows SmartScreen.
    target: [{ target: 'zip', arch: ['x64'] }],
    icon: 'icons/icon.ico',
    artifactName: `io-win-\${arch}${suffix}.\${ext}`,
  },

  linux: {
    target: [{ target: 'AppImage', arch: ['x64', 'arm64'] }],
    icon: 'icons/icon.png',
    category: 'Office',
    synopsis: 'Ask questions about a folder of files, without the files leaving.',
    artifactName: `io-linux-\${arch}${suffix}.\${ext}`,
  },

  mac: {
    target: [{ target: 'dmg', arch: ['arm64'] }],
    icon: 'icons/icon.icns',
    category: 'public.app-category.productivity',
    artifactName: `io-mac-\${arch}${suffix}.\${ext}`,
    // Unsigned and un-notarized for the event: Gatekeeper wants right-click -> Open once.
    identity: null,
  },

  // Nothing is signed. Say so out loud rather than letting a build quietly try and fail.
  forceCodeSigning: false,
};
