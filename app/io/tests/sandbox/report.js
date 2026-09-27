#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const REQUIRED_TARGETS = ['linux-x64', 'darwin-x64', 'darwin-arm64', 'win32-x64'];
const PROPERTY_IDS = [
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

const KNOWN_STATUSES = new Set(['PASS', 'VIOLATION', 'CONTROL ERROR', 'EXECUTION ERROR', 'FAIL']);
const REQUIRED_TARGET_SET = new Set(REQUIRED_TARGETS);
const PROPERTY_SET = new Set(PROPERTY_IDS);

function walkJsonFiles(root) {
  const files = [];
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

function readJson(file) {
  const raw = fs.readFileSync(file, 'utf8');
  return JSON.parse(raw);
}

function humanName(id) {
  if (PROPERTY_NAMES[id]) return PROPERTY_NAMES[id];
  if (id.startsWith('child:')) {
    const base = id.slice('child:'.length);
    return `Child ${PROPERTY_NAMES[base] || `${base} blocked`}`;
  }
  if (id.startsWith('tcp:')) return `TCP ${id.slice('tcp:'.length)}`;
  return id;
}

function emptyTarget(target) {
  return {
    target,
    state: 'MISSING',
    source: null,
    sources: [],
    reportOverall: null,
    reportError: null,
    cleanupError: null,
    notes: [],
    properties: Object.fromEntries(PROPERTY_IDS.map(id => [id, 'MISSING'])),
  };
}

function analyzeReport(file, report) {
  const issues = [];
  const outcome = {
    file,
    target: typeof report?.target === 'string' ? report.target : null,
    reportOverall: typeof report?.overall === 'string' ? report.overall : null,
    reportError: report && Object.prototype.hasOwnProperty.call(report, 'error') ? report.error : null,
    cleanupError: report && Object.prototype.hasOwnProperty.call(report, 'cleanupError') ? report.cleanupError : null,
    notes: issues,
    properties: Object.fromEntries(PROPERTY_IDS.map(id => [id, 'ERROR'])),
    state: 'ERROR',
    validTarget: false,
    validStructure: false,
  };

  if (!report || typeof report !== 'object' || Array.isArray(report)) {
    issues.push(`Malformed JSON object in ${file}`);
    return outcome;
  }

  if (report.schema !== 1) {
    issues.push(`Unexpected schema ${report.schema} in ${file}`);
    return outcome;
  }

  if (!outcome.target || !REQUIRED_TARGET_SET.has(outcome.target)) {
    issues.push(`Unexpected or missing target in ${file}`);
    return outcome;
  }

  if (outcome.reportOverall !== 'PASS' && outcome.reportOverall !== 'FAIL') {
    issues.push(`Unexpected overall status ${outcome.reportOverall} in ${file}`);
  }

  if (outcome.reportError != null) {
    issues.push(`report.error present for ${outcome.target}`);
  }
  if (outcome.cleanupError != null) {
    issues.push(`report.cleanupError present for ${outcome.target}`);
  }

  const properties = Array.isArray(report.properties) ? report.properties : null;
  if (!properties) {
    issues.push(`Missing properties array for ${outcome.target}`);
    return outcome;
  }

  const seen = new Set();
  let hasUnknownStatus = false;
  let hasUnexpectedProperty = false;
  let hasMissingProperty = false;
  for (const prop of properties) {
    if (!prop || typeof prop !== 'object' || Array.isArray(prop)) {
      issues.push(`Malformed property entry for ${outcome.target}`);
      continue;
    }
    const id = prop.id;
    const status = prop.status;
    if (typeof id !== 'string') {
      issues.push(`Property entry missing id for ${outcome.target}`);
      continue;
    }
    if (seen.has(id)) {
      issues.push(`Duplicate property ${id} for ${outcome.target}`);
      continue;
    }
    seen.add(id);
    if (!PROPERTY_SET.has(id)) {
      hasUnexpectedProperty = true;
      issues.push(`Unexpected property ${id} for ${outcome.target}`);
      continue;
    }
    if (typeof status !== 'string') {
      hasUnknownStatus = true;
      issues.push(`Missing status for ${id} in ${outcome.target}`);
      continue;
    }
    if (!KNOWN_STATUSES.has(status)) {
      hasUnknownStatus = true;
      issues.push(`Unknown status ${status} for ${id} in ${outcome.target}`);
      continue;
    }
    outcome.properties[id] = status;
  }

  for (const id of PROPERTY_IDS) {
    if (!seen.has(id)) {
      hasMissingProperty = true;
      issues.push(`Missing property ${id} for ${outcome.target}`);
    }
  }

  const allPass = PROPERTY_IDS.every(id => outcome.properties[id] === 'PASS');
  const onlyKnownStatuses = PROPERTY_IDS.every(id => outcome.properties[id] === 'PASS' || outcome.properties[id] === 'VIOLATION' || outcome.properties[id] === 'CONTROL ERROR' || outcome.properties[id] === 'EXECUTION ERROR' || outcome.properties[id] === 'FAIL');
  const fatal = issues.length > 0 || hasUnknownStatus || hasUnexpectedProperty || hasMissingProperty || outcome.reportError != null || outcome.cleanupError != null || outcome.reportOverall == null || outcome.reportOverall === 'PASS' && !allPass || outcome.reportOverall === 'FAIL' && allPass || !onlyKnownStatuses;

  if (!fatal && allPass && outcome.reportOverall === 'PASS') {
    outcome.state = 'PASS';
  } else if (!fatal && !allPass && outcome.reportOverall === 'FAIL') {
    outcome.state = 'FAIL';
  } else {
    outcome.state = 'ERROR';
    if (outcome.reportOverall === 'PASS' && !allPass) {
      issues.push(`overall PASS disagrees with property statuses for ${outcome.target}`);
    }
    if (outcome.reportOverall === 'FAIL' && allPass) {
      issues.push(`overall FAIL disagrees with all-PASS properties for ${outcome.target}`);
    }
  }

  outcome.validTarget = true;
  outcome.validStructure = !fatal;
  return outcome;
}

function loadArtifacts(root) {
  const diagnostics = [];
  const entries = new Map();
  const orphanFiles = [];
  if (!fs.existsSync(root)) {
    diagnostics.push(`Artifact root does not exist: ${root}`);
    return {diagnostics, entries, orphanFiles};
  }

  for (const file of walkJsonFiles(root)) {
    let report;
    try {
      report = readJson(file);
    } catch (error) {
      diagnostics.push(`Malformed JSON in ${file}: ${error.message}`);
      orphanFiles.push(file);
      continue;
    }
    const analyzed = analyzeReport(file, report);
    if (!analyzed.validTarget) {
      orphanFiles.push(file);
      diagnostics.push(...analyzed.notes);
      continue;
    }
    const target = analyzed.target;
    const previous = entries.get(target);
    if (!previous) {
      entries.set(target, {
        target,
        state: analyzed.state,
        source: file,
        sources: [file],
        reportOverall: analyzed.reportOverall,
        reportError: analyzed.reportError,
        cleanupError: analyzed.cleanupError,
        notes: [...analyzed.notes],
        properties: {...analyzed.properties},
        validStructure: analyzed.validStructure,
      });
      continue;
    }

    previous.state = 'ERROR';
    previous.sources.push(file);
    previous.notes.push(`Duplicate target artifact at ${file}`);
    previous.notes.push(...analyzed.notes);
    previous.validStructure = false;
  }

  return {diagnostics, entries, orphanFiles};
}

function buildMatrix(root, outDir) {
  const {diagnostics, entries, orphanFiles} = loadArtifacts(root);
  const targets = {};
  const rows = PROPERTY_IDS.map(id => ({id, name: humanName(id), cells: {}}));

  for (const target of REQUIRED_TARGETS) {
    const entry = entries.get(target);
    if (!entry) {
      targets[target] = emptyTarget(target);
      continue;
    }
    targets[target] = {
      target,
      state: entry.state,
      source: entry.source,
      sources: entry.sources,
      reportOverall: entry.reportOverall,
      reportError: entry.reportError,
      cleanupError: entry.cleanupError,
      notes: entry.notes,
      properties: entry.properties,
    };
  }

  for (const row of rows) {
    for (const target of REQUIRED_TARGETS) {
      const entry = targets[target];
      if (entry.state === 'MISSING') {
        row.cells[target] = 'MISSING';
      } else if (entry.state === 'PASS' || entry.state === 'FAIL') {
        row.cells[target] = entry.properties[row.id] || 'ERROR';
      } else {
        row.cells[target] = 'ERROR';
      }
    }
  }

  const requiredPass = REQUIRED_TARGETS.every(target => targets[target].state === 'PASS');
  const matrix = {
    schema: 1,
    root: path.resolve(root),
    outputDir: path.resolve(outDir),
    requiredTargets: REQUIRED_TARGETS,
    propertyIds: PROPERTY_IDS,
    generatedAt: new Date().toISOString(),
    overall: requiredPass && diagnostics.length === 0 && orphanFiles.length === 0 ? 'PASS' : 'FAIL',
    diagnostics,
    orphanFiles,
    targets,
    rows,
  };

  return matrix;
}

function renderMarkdown(matrix) {
  const lines = [];
  lines.push('# Sandbox conformance matrix');
  lines.push('');
  lines.push(`Root: \`${matrix.root}\``);
  lines.push(`Output: \`${matrix.outputDir}\``);
  lines.push(`Overall: **${matrix.overall}**`);
  lines.push('');
  lines.push(`Required targets: ${matrix.requiredTargets.map(t => `\`${t}\``).join(', ')}`);
  lines.push('');
  lines.push('| Target | State | Source |');
  lines.push('|---|---|---|');
  for (const target of matrix.requiredTargets) {
    const entry = matrix.targets[target];
    const source = entry.sources && entry.sources.length ? entry.sources.join('<br>') : '';
    lines.push(`| ${target} | ${entry.state} | ${source} |`);
  }
  lines.push('');
  lines.push('| Property ID | Name | ' + matrix.requiredTargets.join(' | ') + ' |');
  lines.push(`|---|---|${matrix.requiredTargets.map(() => '---').join('|')}|`);
  for (const row of matrix.rows) {
    lines.push(`| ${row.id} | ${row.name} | ${matrix.requiredTargets.map(target => row.cells[target]).join(' | ')} |`);
  }
  if (matrix.diagnostics.length || matrix.orphanFiles.length) {
    lines.push('');
    lines.push('## Notes');
    for (const note of matrix.diagnostics) lines.push(`- ${note}`);
    for (const file of matrix.orphanFiles) lines.push(`- Unassigned results file: ${file}`);
  }
  lines.push('');
  return lines.join('\n');
}

function writeOutputs(matrix, outDir) {
  fs.mkdirSync(outDir, {recursive: true});
  const json = JSON.stringify(matrix, null, 2);
  const markdown = renderMarkdown(matrix);
  fs.writeFileSync(path.join(outDir, 'matrix.json'), json);
  fs.writeFileSync(path.join(outDir, 'matrix.md'), markdown);
  if (process.env.GITHUB_STEP_SUMMARY) {
    const summaryPath = process.env.GITHUB_STEP_SUMMARY;
    fs.mkdirSync(path.dirname(summaryPath), {recursive: true});
    fs.appendFileSync(summaryPath, `${markdown}\n`);
  }
  return markdown;
}

function main(argv = process.argv.slice(2)) {
  const artifactRoot = argv[0] ? path.resolve(argv[0]) : null;
  const outputDir = argv[1] ? path.resolve(argv[1]) : artifactRoot;
  if (!artifactRoot) {
    console.error('Usage: node report.js <artifact-root> [output-dir]');
    return 1;
  }
  const matrix = buildMatrix(artifactRoot, outputDir);
  const markdown = writeOutputs(matrix, outputDir);
  if (process.stdout.isTTY || process.env.CI !== 'true') {
    process.stdout.write(`${markdown}\n`);
  }
  return matrix.overall === 'PASS' ? 0 : 1;
}

if (require.main === module) {
  process.exitCode = main();
}

module.exports = {
  REQUIRED_TARGETS,
  PROPERTY_IDS,
  buildMatrix,
  renderMarkdown,
  main,
};
