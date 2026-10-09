import { readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

import { lint, readConfig } from 'markdownlint/promise';

export const DEFAULT_ROOTS = [
  'fern/docs/pages',
  'doc-infrastructure/templates',
];

export const DEFAULT_CONFIG = '.markdownlint.json';

export function collectMdxFiles(roots) {
  const files = [];
  const visitedDirectories = new Set();

  for (const root of roots) {
    walkDocumentation(root, files, visitedDirectories);
  }

  files.sort((left, right) => left.localeCompare(right));
  return files;
}

function walkDocumentation(directory, files, visitedDirectories) {
  let resolvedDirectory;
  try {
    resolvedDirectory = path.resolve(directory);
    if (visitedDirectories.has(resolvedDirectory)) {
      return;
    }
    visitedDirectories.add(resolvedDirectory);
  } catch (error) {
    throw new Error(`Unable to read '${directory}': ${error.message}`);
  }

  let entries;
  try {
    entries = readdirSync(directory, { withFileTypes: true });
  } catch (error) {
    throw new Error(`Unable to read '${directory}': ${error.message}`);
  }

  for (const entry of entries) {
    const fullPath = path.join(directory, entry.name);
    const kind = fileKind(entry, fullPath);
    if (kind === 'directory') {
      walkDocumentation(fullPath, files, visitedDirectories);
    } else if (kind === 'file' && entry.name.endsWith('.mdx')) {
      files.push(fullPath);
    }
  }
}

function fileKind(entry, fullPath) {
  if (entry.isDirectory()) {
    return 'directory';
  }
  if (entry.isFile()) {
    return 'file';
  }
  if (!entry.isSymbolicLink()) {
    return 'other';
  }

  try {
    const stats = statSync(fullPath);
    if (stats.isDirectory()) {
      return 'directory';
    }
    if (stats.isFile()) {
      return 'file';
    }
  } catch (error) {
    throw new Error(`Unable to read '${fullPath}': ${error.message}`);
  }
  return 'other';
}

export function formatDiagnostic(filePath, error) {
  const rule = error.ruleNames?.[0] ?? 'markdownlint';
  const detail = error.errorDetail ? ` [${error.errorDetail}]` : '';
  const context = error.errorContext ? ` [Context: "${error.errorContext}"]` : '';
  return `${filePath}:${error.lineNumber} ${rule} ${error.ruleDescription}${detail}${context}`;
}

export async function lintDocumentation({
  roots = DEFAULT_ROOTS,
  configPath = DEFAULT_CONFIG,
} = {}) {
  const config = await readConfig(configPath);
  const files = collectMdxFiles(roots);
  if (files.length === 0) {
    throw new Error(
      'No .mdx files were found in the documentation directories.',
    );
  }

  let results;
  try {
    results = await lint({ files, config });
  } catch (error) {
    throw new Error(`Unable to read a documentation file: ${error.message}`);
  }

  const diagnostics = [];
  for (const [filePath, errors] of Object.entries(results)) {
    for (const error of errors ?? []) {
      diagnostics.push(formatDiagnostic(filePath, error));
    }
  }
  diagnostics.sort((left, right) => left.localeCompare(right));
  return { files, diagnostics };
}

function parseLintArgs(argv) {
  const { values, positionals } = parseArgs({
    args: argv,
    options: {
      config: { type: 'string', default: DEFAULT_CONFIG },
    },
    allowPositionals: true,
  });
  return {
    configPath: values.config,
    roots: positionals.length > 0 ? positionals : DEFAULT_ROOTS,
  };
}

export async function main(argv = process.argv.slice(2)) {
  try {
    const { files, diagnostics } = await lintDocumentation(parseLintArgs(argv));
    if (diagnostics.length > 0) {
      for (const diagnostic of diagnostics) {
        console.error(diagnostic);
      }
      return 1;
    }
    console.log(`Linted ${files.length} Markdown files.`);
    return 0;
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    return 1;
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  process.exitCode = await main();
}
