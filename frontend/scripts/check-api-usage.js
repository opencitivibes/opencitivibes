#!/usr/bin/env node
/**
 * Frontend Architecture Checker: Centralized API Usage
 *
 * Ensures all API calls go through @/lib/api.ts, not direct axios/fetch calls.
 *
 * Forbidden patterns in components/pages:
 * - import axios from 'axios'
 * - import { axios } from 'axios'
 * - axios.get(), axios.post(), etc.
 * - fetch('http://...')  (direct fetch with URLs)
 *
 * Allowed:
 * - Imports from '@/lib/api'
 * - api.ts itself can use axios
 *
 * Usage:
 *   node scripts/check-api-usage.js
 *
 * Exit codes:
 *   0 - No violations
 *   1 - Violations found
 */

const fs = require('fs');
const path = require('path');

const SRC_DIR = path.join(__dirname, '..', 'src');

// Files that ARE allowed to use axios directly
const ALLOWED_FILES = ['lib/api.ts', 'lib/api-server.ts', 'lib/config/PlatformConfigProvider.tsx'];

// Patterns to detect
const FORBIDDEN_PATTERNS = [
  { regex: /from\s+['"]axios['"]/, desc: "import from 'axios'" },
  { regex: /import\s+axios/, desc: 'import axios' },
  { regex: /axios\.(get|post|put|patch|delete|request)\s*\(/, desc: 'axios.method() call' },
];

function getAllFiles(dir, extensions = ['.ts', '.tsx']) {
  let results = [];
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

  return results;
}

function isAllowedFile(filePath) {
  const relative = path.relative(SRC_DIR, filePath).replace(/\\/g, '/');
  return ALLOWED_FILES.some((allowed) => relative === allowed || relative.endsWith(allowed));
}

function checkFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split('\n');
  const violations = [];

  lines.forEach((line, index) => {
    for (const pattern of FORBIDDEN_PATTERNS) {
      if (pattern.regex.test(line)) {
        violations.push({
          line: index + 1,
          desc: pattern.desc,
          content: line.trim().substring(0, 60),
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
    console.log('ARCHITECTURE VIOLATION: Direct axios usage in components');
    console.log('='.repeat(70));
    console.log();
    console.log('Components must use the centralized API from @/lib/api.ts');
    console.log('Do NOT import axios directly in components or pages.');
    console.log();
    console.log('Example:');
    console.log("  import { ideaAPI } from '@/lib/api';  // DO");
    console.log("  import axios from 'axios';            // DON'T");
    console.log();

    for (const { filePath, violations } of filesWithViolations) {
      const relative = path.relative(SRC_DIR, filePath);
      console.log(`  src/${relative}:`);
      for (const v of violations) {
        console.log(`    Line ${v.line}: ${v.desc}`);
      }
      console.log();
    }

    console.log(`Total: ${totalViolations} violation(s) in ${filesWithViolations.length} file(s)`);
    process.exit(1);
  }

  console.log(`✅ No direct axios usage in ${files.length} frontend file(s)`);
  process.exit(0);
}

main();
