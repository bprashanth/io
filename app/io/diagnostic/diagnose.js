#!/usr/bin/env node

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');

const appPackage = require('../package.json');
const sandbox = require('../tests/sandbox/run.js');

const REQUIRED_IDS = [
  'workspace_read',
  'workspace_write',
  'outside_read',
  'outside_write',
  'link_read',
  'link_write',
  'child_execution',
  'child:outside_read',
  'child:outside_write',
  'child:link_read',
  'child:link_write',
  'tcp:loopback',
  'child:tcp:loopback',
  'tcp:nonloopback',
  'child:tcp:nonloopback',
  'tcp:internet',
  'child:tcp:internet',
];

const PROPERTY_NAMES = {
  workspace_read: 'Workspace read',
  workspace_write: 'Workspace write',
  outside_read: 'Outside read blocked',
  outside_write: 'Outside write blocked',
  link_read: 'Symlink/junction read blocked',
  link_write: 'Symlink/junction write blocked',
  child_execution: 'Child interpreter works',
};

const RESULT_TO_CAPABILITY = {
  PASS: 'PASS',
  VIOLATION: 'FAIL',
  'CONTROL ERROR': 'INCONCLUSIVE',
  'EXECUTION ERROR': 'INCONCLUSIVE',
  FAIL: 'INCONCLUSIVE',
  ERROR: 'INCONCLUSIVE',
  MISSING: 'INCONCLUSIVE',
};

function parseArgs(argv) {
  const args = {runtime: null, out: null, reportExisting: null};
  for (let i = 0; i < argv.length; i += 1) {
    const value = argv[i];
    if (value === '--runtime') {
      args.runtime = argv[++i];
    } else if (value.startsWith('--runtime=')) {
      args.runtime = value.slice('--runtime='.length);
    } else if (value === '--out') {
      args.out = argv[++i];
    } else if (value.startsWith('--out=')) {
      args.out = value.slice('--out='.length);
    } else if (value === '--report-existing') {
      args.reportExisting = argv[++i];
    } else if (value.startsWith('--report-existing=')) {
      args.reportExisting = value.slice('--report-existing='.length);
    } else if (value === '--help' || value === '-h') {
      args.help = true;
    } else {
      throw new Error(`Unknown argument: ${value}`);
    }
  }
  return args;
}

function usage() {
  return [
    'Usage: node app/io/diagnostic/diagnose.js --runtime <runtime-dir> --out <output-dir> [--report-existing <results-root>]',
    '',
    'The diagnostic either runs the sandbox suite into <output-dir>/raw or reclassifies',
    'an existing results.json tree when --report-existing is supplied.',
  ].join('\n');
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function walkResultsFiles(root) {
  const files = [];
  if (!root || !fs.existsSync(root)) return files;
  const stack = [root];
  while (stack.length) {
    const current = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(current, {withFileTypes: true});
    } catch {
      continue;
    }
    for (const entry of entries) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(full);
      } else if (entry.isFile() && entry.name === 'results.json') {
        files.push(full);
      }
    }
  }
  return files.sort();
}

function resolveRuntime(runtime) {
  if (!runtime) return null;
  try {
    return fs.realpathSync(runtime);
  } catch {
    return path.resolve(runtime);
  }
}

function resolveResultsSource(reportExisting) {
  if (!reportExisting) return null;
  const stat = fs.existsSync(reportExisting) ? fs.statSync(reportExisting) : null;
  if (stat?.isFile()) {
    return path.resolve(reportExisting);
  }
  const files = walkResultsFiles(reportExisting);
  if (files.length === 1) return files[0];
  return files;
}

function propertyIndex(properties) {
  const index = new Map();
  const issues = [];
  if (!Array.isArray(properties)) {
    return {index, issues: ['Missing properties array']};
  }
  for (const prop of properties) {
    if (!prop || typeof prop !== 'object' || Array.isArray(prop)) {
      issues.push('Malformed property entry');
      continue;
    }
    if (typeof prop.id !== 'string') {
      issues.push('Property entry missing id');
      continue;
    }
    if (index.has(prop.id)) {
      issues.push(`Duplicate property ${prop.id}`);
      continue;
    }
    index.set(prop.id, prop);
  }
  for (const id of REQUIRED_IDS) {
    if (!index.has(id)) issues.push(`Missing required property ${id}`);
  }
  return {index, issues};
}

function capabilityStatus(rows, structuralIssues, report) {
  if (report?.error) structuralIssues.push(`Launcher error: ${report.error}`);
  if (report?.cleanupError) structuralIssues.push(`Cleanup error: ${report.cleanupError}`);
  if (!Array.isArray(report?.properties)) structuralIssues.push('Report properties were not an array');

  const terminal = [];
  let hasViolation = false;
  let hasInconclusive = structuralIssues.length > 0;
  for (const row of rows) {
    const status = RESULT_TO_CAPABILITY[row.status] || 'INCONCLUSIVE';
    terminal.push(status);
    if (status === 'FAIL') {
      hasViolation = true;
    } else if (status !== 'PASS') {
      hasInconclusive = true;
    }
  }

  if (hasViolation) return 'FAIL';
  if (hasInconclusive) return 'INCONCLUSIVE';
  if (terminal.length !== REQUIRED_IDS.length) return 'INCONCLUSIVE';
  return 'PASS';
}

function summarizeRationale(status, rows, structuralIssues) {
  if (status === 'PASS') return ['All required probes passed and the raw report was complete.'];
  const notes = [];
  if (status === 'FAIL') {
    const failing = rows.find(row => row.status === 'VIOLATION');
    notes.push(failing ? `${failing.name} violated the sandbox contract.` : 'A sandbox violation was recorded.');
  } else {
    notes.push('The diagnostic could not prove the capability because the report was incomplete or the launcher/control was unavailable.');
  }
  for (const issue of structuralIssues) notes.push(issue);
  return notes;
}

function buildProbeResults(report, rows, propertyMap) {
  const runs = report?.runs && typeof report.runs === 'object' ? report.runs : {};
  return rows.map(row => {
    const property = propertyMap.get(row.id) || null;
    const propertyStatus = property ? property.status : null;
    const propertyMatches = propertyStatus === row.status;
    const observed = {};
    for (const [label, run] of Object.entries(runs)) {
      observed[label] = run?.probe?.checks?.[row.id] ?? null;
    }
    let status = RESULT_TO_CAPABILITY[row.status] || 'INCONCLUSIVE';
    if (!property || !propertyMatches) {
      status = row.status === 'VIOLATION' ? 'FAIL' : 'INCONCLUSIVE';
    }
    return {
      id: row.id,
      name: row.name,
      status,
      rawStatus: row.status,
      reason: row.reason,
      reportStatus: propertyStatus,
      observed,
    };
  });
}

function classifyCapability(report, options = {}) {
  const reportSource = options.reportSource || null;
  const reportFile = options.reportFile || null;
  const runtime = options.runtime || null;
  const {index: properties, issues: propertyIssues} = propertyIndex(report?.properties);
  const endpoints = Array.isArray(report?.metadata?.endpoints) ? report.metadata.endpoints : [];
  let evaluatedRows = [];
  let evaluationIssues = [];

  try {
    evaluatedRows = sandbox.evaluate(report?.runs || {}, endpoints);
  } catch (error) {
    evaluationIssues = [`Could not evaluate probe results: ${error.message}`];
  }

  const structuralIssues = [...propertyIssues, ...evaluationIssues];
  if (report?.conformanceEligible === false || report?.candidate || report?.diagnostic) structuralIssues.push('Experimental backend report is not eligible for product qualification');
  if (report?.overall !== 'PASS') structuralIssues.push('Underlying suite did not pass');
  for (const row of evaluatedRows) {
    const prop = properties.get(row.id);
    if (!prop) continue;
    if (prop.status !== row.status) structuralIssues.push(`Property status mismatch for ${row.id}`);
  }
  const status = capabilityStatus(evaluatedRows, structuralIssues, report);
  const source = {
    mode: reportSource ? 'report-existing' : 'live',
    runtime,
    reportSource,
  };

  const rawRoot = reportSource
    ? (fs.existsSync(reportSource) && fs.statSync(reportSource).isDirectory() ? reportSource : path.dirname(reportFile || reportSource))
    : (reportFile ? path.dirname(reportFile) : null);
  const rawResults = reportFile
    || (reportSource && fs.existsSync(reportSource) && fs.statSync(reportSource).isFile() ? reportSource : null);
  const rawSummary = rawResults ? path.join(path.dirname(rawResults), 'summary.md') : null;

  return {
    schema: 1,
    status,
    executionMode: 'remote',
    routingChanged: false,
    version: {
      io: appPackage.version,
      codex: report?.metadata?.codexVersion ?? null,
      node: process.version,
    },
    platform: {
      target: report?.target ?? `${process.platform}-${process.arch}`,
      os: report?.metadata?.os ?? os.type(),
      arch: report?.metadata?.arch ?? process.arch,
      release: report?.metadata?.release ?? os.release(),
      version: report?.metadata?.version ?? os.version(),
    },
    build: {
      commit: report?.metadata?.commit ?? null,
      codexPackage: report?.metadata?.codexPackage ?? null,
    },
    backend: {
      name: report?.diagnostic || (String(report?.target || process.platform).startsWith('win32') ? 'unelevated' : String(report?.target || process.platform).startsWith('darwin') ? 'seatbelt' : 'linux-bwrap'),
      launcher: 'codex sandbox',
    },
    source,
    probes: buildProbeResults(report, evaluatedRows, properties),
    rationale: summarizeRationale(status, evaluatedRows, structuralIssues),
    rawReports: {
      preserved: true,
      root: rawRoot,
      results: rawResults,
      summary: rawSummary,
    },
  };
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.writeFileSync(file, JSON.stringify(value, null, 2));
}

function runSandbox(runtime, outDir, logDir) {
  const script = path.join(__dirname, '../tests/sandbox/run.js');
  fs.mkdirSync(outDir, {recursive: true});
  const args = [script, '--runtime', runtime, '--out', outDir];
  const result = spawnSync(process.execPath, args, {
    cwd: path.join(__dirname, '..'),
    encoding: 'utf8',
    timeout: 5 * 60 * 1000,
    maxBuffer: 10 * 1024 * 1024,
    env: process.env,
  });
  fs.writeFileSync(path.join(logDir, 'launcher.stdout.txt'), result.stdout ?? '');
  fs.writeFileSync(path.join(logDir, 'launcher.stderr.txt'), result.stderr ?? '');
  return result;
}

function loadReport(reportPath) {
  if (!reportPath) return {report: null, reportFile: null, reportRoot: null, issue: 'No report source provided'};
  const stat = fs.existsSync(reportPath) ? fs.statSync(reportPath) : null;
  if (stat?.isFile()) {
    return {report: readJson(reportPath), reportFile: reportPath, reportRoot: path.dirname(reportPath), issue: null};
  }
  if (!stat?.isDirectory()) {
    return {report: null, reportFile: null, reportRoot: null, issue: `Report source does not exist: ${reportPath}`};
  }
  const files = walkResultsFiles(reportPath);
  if (files.length !== 1) {
    return {
      report: null,
      reportFile: null,
      reportRoot: reportPath,
      issue: files.length === 0 ? `No results.json found under ${reportPath}` : `Multiple results.json files found under ${reportPath}`,
    };
  }
  return {report: readJson(files[0]), reportFile: files[0], reportRoot: reportPath, issue: null};
}

function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (args.help) {
    console.log(usage());
    return 0;
  }
  if (!args.runtime || !args.out) {
    console.error(usage());
    return 2;
  }

  const outDir = path.resolve(args.out);
  const rawDir = path.join(outDir, 'raw-' + Date.now());
  fs.mkdirSync(outDir, {recursive: true});

  let reportFile = null;
  let reportRoot = null;
  let report = null;
  const runtime = resolveRuntime(args.runtime);
  const sourceMode = args.reportExisting ? 'report-existing' : 'live';
  const sourcePath = args.reportExisting ? path.resolve(args.reportExisting) : null;

  if (args.reportExisting) {
    const loaded = loadReport(args.reportExisting);
    report = loaded.report;
    reportFile = loaded.reportFile;
    reportRoot = loaded.reportRoot;
    if (loaded.issue) {
      const capability = classifyCapability(report, {runtime, reportSource: sourcePath});
      capability.status = 'INCONCLUSIVE';
      capability.rationale = [loaded.issue, ...capability.rationale];
      capability.source.mode = sourceMode;
      capability.source.reportSource = sourcePath;
      capability.rawReports.root = reportRoot;
      capability.rawReports.results = reportFile;
      writeJson(path.join(outDir, 'capability.json'), capability);
      return 0;
    }
  } else {
    const launched = runSandbox(runtime, rawDir, rawDir);
    const loaded = loadReport(rawDir);
    report = loaded.report;
    reportFile = loaded.reportFile;
    reportRoot = loaded.reportRoot;
    if (!report && launched.error) {
      const capability = {
        schema: 1,
        status: 'INCONCLUSIVE',
        executionMode: 'remote',
        routingChanged: false,
        version: {io: appPackage.version, codex: null, node: process.version},
        platform: {target: `${process.platform}-${process.arch}`, os: os.type(), arch: process.arch},
        build: {commit: null, codexPackage: null},
        backend: {name: 'sandbox', launcher: 'codex sandbox'},
        source: {mode: sourceMode, runtime, reportSource: null},
        probes: [],
        rationale: [`Sandbox launcher failed: ${launched.error.message}`],
        rawReports: {
          preserved: true,
          root: rawDir,
          results: null,
          summary: null,
        },
      };
      writeJson(path.join(outDir, 'capability.json'), capability);
      return 0;
    }
  }

  const capability = classifyCapability(report, {
    runtime,
    reportSource: sourceMode === 'report-existing' ? sourcePath : reportRoot,
    reportFile,
  });
  capability.source.mode = sourceMode;
  capability.source.runtime = runtime;
  capability.source.reportSource = sourceMode === 'report-existing' ? (reportFile || sourcePath) : (reportFile || reportRoot);
  capability.rawReports.root = reportRoot;
  capability.rawReports.results = reportFile;
  capability.rawReports.summary = reportFile ? path.join(path.dirname(reportFile), 'summary.md') : capability.rawReports.summary;

  writeJson(path.join(outDir, 'capability.json'), capability);
  return capability.status === 'PASS' ? 0 : 1;
}

if (require.main === module) {
  try {
    process.exitCode = main();
  } catch (error) {
    console.error(error.stack || error.message);
    process.exitCode = 1;
  }
}

module.exports = {
  REQUIRED_IDS,
  parseArgs,
  resolveRuntime,
  resolveResultsSource,
  walkResultsFiles,
  propertyIndex,
  capabilityStatus,
  summarizeRationale,
  buildProbeResults,
  classifyCapability,
  loadReport,
  main,
};
