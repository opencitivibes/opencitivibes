#!/usr/bin/env node
/**
 * Frontend Architecture Checker: Hardcoded URLs
 *
 * Detects hardcoded API URLs that should use environment variables.
 * These cause CORS issues and break in different environments.
 *
 * Forbidden patterns:
 * - http://localhost:8000
 * - http://127.0.0.1:8000
 * - Hardcoded API paths without env vars
 *
 * Allowed:
 * - process.env.NEXT_PUBLIC_API_URL
 * - Config files that SET the fallback
 *
 * Usage:
 *   node scripts/check-hardcoded-urls.js
 *
 * Exit codes:
 *   0 - No violations
 *   1 - Violations found
 */

const fs = require('fs');
const path = require('path');

const SRC_DIR = path.join(__dirname, '..', 'src');

// Files that ARE allowed to have fallback URLs (config/setup files)
const ALLOWED_FILES = [
  'lib/api.ts',
  'lib/api-server.ts',
  'lib/config/PlatformConfigProvider.tsx',
  'app/sitemap.ts',
  'app/layout.tsx', // May need API URL for metadata
];

// Patterns to detect hardcoded URLs
const FORBIDDEN_PATTERNS = [
  {
    regex: /['"`]https?:\/\/localhost:\d+/,
    desc: 'Hardcoded localhost URL',
  },
  {
    regex: /['"`]https?:\/\/127\.0\.0\.1:\d+/,
    desc: 'Hardcoded 127.0.0.1 URL',
  },
  {
    regex: /['"`]https?:\/\/192\.168\.\d+\.\d+:\d+/,
    desc: 'Hardcoded local network URL',
  },
  {
    regex: /fetch\s*\(\s*['"`]https?:\/\//,
    desc: 'fetch() with hardcoded URL',
  },
];

// Lines to ignore (contain env var fallback pattern)
const IGNORE_IF_CONTAINS = ['process.env.', 'NEXT_PUBLIC_', '// fallback', "|| 'http", "|| 'http"];

function getAllFiles(dir, extensions = ['.ts', '.tsx']) {
  let results = [];

  try {
    const list = fs.readdirSync(dir);

    for (const file of list) {
      const filePath = path.join(dir, file);
      const stat = fs.statSync(filePath);

      if (stat.isDirectory()) {
        results = results.concat(getAllFiles(filePath, extensions));
      } else if (extensions.some((ext) => file.endsWith(ext))) {
        results.push(filePath);
      }
    }
  } catch {
    // Directory doesn't exist or can't be read
  }

  return results;
}

function isAllowedFile(filePath) {
  const relative = path.relative(SRC_DIR, filePath).replace(/\\/g, '/');
  return ALLOWED_FILES.some((allowed) => relative === allowed || relative.endsWith(allowed));
}

function shouldIgnoreLine(line) {
  return IGNORE_IF_CONTAINS.some((pattern) => line.includes(pattern));
}

function checkFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split('\n');
  const violations = [];

  lines.forEach((line, index) => {
    // Skip lines that are env var fallbacks
    if (shouldIgnoreLine(line)) return;

    for (const pattern of FORBIDDEN_PATTERNS) {
      if (pattern.regex.test(line)) {
        violations.push({
          line: index + 1,
          desc: pattern.desc,
          content: line.trim().substring(0, 80),
        });
      }
    }
  });

  return violations;
}

function main() {
  const files = getAllFiles(SRC_DIR);
  let totalViolations = 0;
  const filesWithViolations = [];

  for (const filePath of files) {
    if (isAllowedFile(filePath)) continue;

    const violations = checkFile(filePath);
    if (violations.length > 0) {
      filesWithViolations.push({ filePath, violations });
      totalViolations += violations.length;
    }
  }

  if (filesWithViolations.length > 0) {
    console.log('='.repeat(70));
    console.log('ARCHITECTURE VIOLATION: Hardcoded URLs in frontend');
    console.log('='.repeat(70));
    console.log();
    console.log('Hardcoded URLs cause CORS issues and break in different environments.');
    console.log('Use environment variables via the centralized API config.');
    console.log();
    console.log('Example:');
    console.log("  import { getApiUrl } from '@/lib/api';     // DO");
    console.log("  fetch('http://localhost:8000/api/...')     // DON'T");
    console.log();

    for (const { filePath, violations } of filesWithViolations) {
      const relative = path.relative(SRC_DIR, filePath);
      console.log(`  src/${relative}:`);
      for (const v of violations) {
        console.log(`    Line ${v.line}: ${v.desc}`);
        console.log(`      ${v.content}`);
      }
      console.log();
    }

    console.log(`Total: ${totalViolations} violation(s) in ${filesWithViolations.length} file(s)`);
    console.log();
    console.log('Fix: Use process.env.NEXT_PUBLIC_API_URL or import from @/lib/api');
    process.exit(1);
  }

  console.log(`✅ No hardcoded URLs in ${files.length} frontend file(s)`);
  process.exit(0);
}

main();
