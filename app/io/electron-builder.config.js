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
  // The organizer's projector board. Stdlib only, so the bundled python can run it and an
  // organizer does not need a git checkout or a system python to put it on screen.
  { from: 'room_server.py', to: 'io/room_server.py' },
  // The privacy server, for the same reason: stdlib only, so the bundled python can run
  // it and an organizer without a git checkout can still stand one up for a laptop that
  // cannot run the scanner itself.
  { from: 'privacy_server.py', to: 'io/privacy_server.py' },
  { from: 'engine', to: 'io/engine', filter: ['**/*.py'] },
  { from: 'ui', to: 'io/ui' },
];

// A participant copies this whole folder off a USB stick, and on Windows that is a slow,
// per-file operation - so the file COUNT is what hurts, not the megabytes. Roughly 40% of
// the runtime is files that are never read while the app runs:
//
//   torch/include   C++ headers, read only when compiling an extension against torch.
//                   Nothing here does; verified nothing imports torch.utils.cpp_extension.
//   */tests/        the test suites packages ship - mostly pandas, sympy, numpy, networkx.
//   *.pyi           type stubs, for type checkers only.
//   *.a  *.lib      static and import libraries, inputs to a linker, not to python.
//   licenses/       third-party attribution text nested inside dist-info. Also the only
//                   thing in the pack long enough to hit Windows' 260-character path limit.
//
// Directories named tests/ or test/ only - never a file called tests.py. jinja2/tests.py
// is a real module that jinja2 imports at module level, and matching on the name rather
// than the directory would silently break every template. mpmath imports its own .tests
// too, but from inside runtests(), so it never runs here.
//
// Checked by pruning a real runtime and re-running the scanner over a fixed corpus: the
// same spans, labels and offsets came back, and service.py, pandas, torch, transformers,
// gliner, sympy, mpmath, jinja2, networkx, onnxruntime and the pdf reader all still import.
const RUNTIME_FILTER = [
  '**/*',
  '!**/site-packages/torch/include/**',
  '!**/site-packages/**/tests/**',
  '!**/site-packages/**/test/**',
  '!**/*.dist-info/licenses/**',
  '!**/*.pyi',
  '!**/*.a',
  '!**/*.lib',
];

if (FAT) {
  for (const part of ['runtime', 'hf-cache']) {
    const src = path.join(PAYLOAD, part);
    if (!fs.existsSync(src)) {
      throw new Error(`IO_FAT=1 but ${src} is missing. Run: node bootstrap.js --dest ${PAYLOAD}`);
    }
    extraResources.push({ from: src, to: part, filter: part === 'runtime' ? RUNTIME_FILTER : undefined });
  }

  // The offline build exists for USB sticks, so ship it already portable: an io-data folder
  // beside the executable is what switches that on, and asking a participant to create a
  // folder before the app will behave is a step that gets skipped. An archive cannot carry
  // an empty directory, so put a readable note in it - which also explains the folder to
  // anyone who finds it and wonders whether it is safe to delete.
  const marker = path.join(PAYLOAD, 'io-data');
  fs.mkdirSync(marker, { recursive: true });
  fs.writeFileSync(path.join(marker, 'README.txt'),
    [
      'This folder is what makes io portable.',
      '',
      'While it sits next to the io program, io keeps everything it writes inside it:',
      'the python it runs on, the on-device scanner, your folder list, your corrections,',
      'and the vault that maps codes back to real names.',
      '',
      'That means you can run io from this drive on someone else\'s computer, point it at',
      'folders on their disk, and leave nothing of yours behind when you unplug it.',
      '',
      'Delete this folder and io goes back to storing its data in your user account',
      'in the normal way.',
      '',
    ].join('\n'));
  // On Windows and Linux ../io-data lands beside the executable. On macOS it lands in
  // io.app/Contents/io-data, because a dmg cannot place a writable folder next to the
  // bundle - runtime.js looks in both places for exactly this reason.
  extraResources.push({ from: marker, to: '../io-data' });
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

  // The launcher goes next to the binary, not into resources/. Linux only: it exists to
  // deal with Chromium's setuid sandbox helper, which Windows and macOS do not have.
  extraFiles: process.platform === 'linux' || process.env.IO_TARGET_LINUX
    ? [{ from: 'launcher/io', to: 'io' }]
    : [],

  linux: {
    // The real binary is io-bin; 'io' is the launcher above. AppImage's AppRun execs the
    // executableName directly and never sees the launcher, so it gets the flag this way.
    executableName: 'io-bin',
    executableArgs: ['--no-sandbox'],
    // tar.gz only. The AppImage was dropped after four separate problems, each verified:
    // it needs libfuse2 that Ubuntu 24.04 no longer ships, so a double-click dies with
    // "dlopen(): error loading libfuse.so.2"; its AppRun execs the binary directly and
    // bypasses the launcher that handles Chromium's setuid sandbox, so it core-dumps the
    // same way the tarball used to (executableArgs only reaches the .desktop entry, which
    // nobody uses when launching the file itself); it doubled the offline payload at about
    // a gigabyte; and the install docs already told people to use the tarball. Extract the
    // tarball anywhere and run ./io.
    target: [{ target: 'tar.gz', arch: ['x64', 'arm64'] }],
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
