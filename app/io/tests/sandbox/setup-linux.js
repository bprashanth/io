// Trusted runner provisioning, separate from the unprivileged conformance commands.
// Apply the SAME narrow userns grant io offers; do not disable AppArmor globally.
const fs = require('fs');
const path = require('path');
const {execFileSync} = require('child_process');
const codex = require('../../codex');
if (process.platform !== 'linux' || process.getuid() === 0) throw Error('Expected ordinary Linux runner account');
const out = path.resolve('sandbox-results');
fs.mkdirSync(out, {recursive: true});
const fix = codex.linuxFix(codex.bundledCodexPath().dir, true);
if (!fix) throw Error('No narrow AppArmor setup available');
const profile = path.join(out, 'io-bwrap.apparmor');
fs.writeFileSync(profile, fix.profile);
execFileSync('sudo', ['-n', 'install', '-m', '644', profile, '/etc/apparmor.d/io-conformance-bwrap'], {stdio: 'inherit'});
execFileSync('sudo', ['-n', 'apparmor_parser', '-r', '/etc/apparmor.d/io-conformance-bwrap'], {stdio: 'inherit'});
console.log('Installed io userns profile. Probe commands still run as the original ordinary user.');
if (process.env.GITHUB_ENV) fs.appendFileSync(process.env.GITHUB_ENV, 'IO_CONFORMANCE_SETUP=io-apparmor-userns\n');
