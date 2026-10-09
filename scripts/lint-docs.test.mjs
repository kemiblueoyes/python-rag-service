import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import {
  chmodSync,
  mkdtempSync,
  mkdirSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { collectMdxFiles } from './lint-docs.mjs';

const scriptPath = fileURLToPath(new URL('./lint-docs.mjs', import.meta.url));
const configPath = fileURLToPath(new URL('../.markdownlint.json', import.meta.url));

const validDocument = `---
title: Example
---

<Card>Component</Card>

A paragraph that satisfies the enabled rules.
`;

function makeTree() {
  const root = mkdtempSync(path.join(tmpdir(), 'lint-docs-'));
  const page = path.join(root, 'fern', 'docs', 'pages', 'nested', 'page.mdx');
  const template = path.join(
    root,
    'doc-infrastructure',
    'templates',
    'nested',
    'template.mdx',
  );
  mkdirSync(path.dirname(page), { recursive: true });
  mkdirSync(path.dirname(template), { recursive: true });
  writeFileSync(page, validDocument);
  writeFileSync(template, validDocument);
  writeFileSync(path.join(root, 'fern', 'docs', 'pages', 'notes.txt'), 'skip');
  writeFileSync(path.join(root, 'fern', 'docs', 'pages', 'nested', 'notes.md'), 'skip');
  mkdirSync(path.join(root, 'other'), { recursive: true });
  writeFileSync(path.join(root, 'other', 'skip.mdx'), validDocument);
  return { root, page, template };
}

function runLint(args) {
  return spawnSync(process.execPath, [scriptPath, ...args], { encoding: 'utf8' });
}

test('includes nested documentation and template files only', () => {
  const { root, page, template } = makeTree();
  try {
    const files = collectMdxFiles([
      path.join(root, 'fern', 'docs', 'pages'),
      path.join(root, 'doc-infrastructure', 'templates'),
    ]);
    assert.deepEqual(files, [template, page].sort((left, right) => left.localeCompare(right)));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('valid MDX and frontmatter pass', () => {
  const { root } = makeTree();
  try {
    const result = runLint([
      '--config',
      configPath,
      path.join(root, 'fern', 'docs', 'pages'),
      path.join(root, 'doc-infrastructure', 'templates'),
    ]);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /Linted 2 Markdown files/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('an enabled-rule violation reports the diagnostic and exits nonzero', () => {
  const { root, page } = makeTree();
  try {
    writeFileSync(page, `${validDocument}\n#NoSpace\n`);
    const result = runLint([
      '--config',
      configPath,
      path.join(root, 'fern', 'docs', 'pages'),
      path.join(root, 'doc-infrastructure', 'templates'),
    ]);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /page\.mdx:\d+ MD018 No space after hash/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('inline rule controls still suppress a violation', () => {
  const { root, page } = makeTree();
  try {
    writeFileSync(
      page,
      `${validDocument}\n<!-- markdownlint-disable MD018 -->\n#NoSpace\n`,
    );
    const result = runLint([
      '--config',
      configPath,
      path.join(root, 'fern', 'docs', 'pages'),
    ]);
    assert.equal(result.status, 0, result.stderr);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('missing and invalid configuration fail', () => {
  const { root } = makeTree();
  try {
    const pages = path.join(root, 'fern', 'docs', 'pages');
    const missing = runLint(['--config', path.join(root, 'missing.json'), pages]);
    assert.notEqual(missing.status, 0);
    assert.match(missing.stderr, /ENOENT|no such file|Unable to/i);

    const invalidPath = path.join(root, 'invalid.json');
    writeFileSync(invalidPath, '{');
    const invalid = runLint(['--config', invalidPath, pages]);
    assert.notEqual(invalid.status, 0);
    assert.match(invalid.stderr, /Unable to parse|JSON/i);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('missing directories, unreadable files, and empty input fail', () => {
  const { root, page } = makeTree();
  try {
    const missing = runLint([
      '--config',
      configPath,
      path.join(root, 'does-not-exist'),
    ]);
    assert.notEqual(missing.status, 0);
    assert.match(missing.stderr, /Unable to read/);

    chmodSync(page, 0);
    const unreadable = runLint([
      '--config',
      configPath,
      path.join(root, 'fern', 'docs', 'pages'),
    ]);
    assert.notEqual(unreadable.status, 0);
    assert.match(unreadable.stderr, /Unable to read a documentation file/);
    chmodSync(page, 0o644);

    const empty = mkdtempSync(path.join(root, 'empty-'));
    const emptyResult = runLint(['--config', configPath, empty]);
    assert.notEqual(emptyResult.status, 0);
    assert.match(emptyResult.stderr, /No \.mdx files were found/);
  } finally {
    chmodSync(page, 0o644);
    rmSync(root, { recursive: true, force: true });
  }
});
