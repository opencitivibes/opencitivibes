/**
 * Script to find and report i18n anti-patterns in the codebase.
 *
 * Run: npx ts-node scripts/migrate-i18n-patterns.ts
 *       or: pnpm exec tsx scripts/migrate-i18n-patterns.ts
 */

import * as fs from 'fs';
import * as path from 'path';
import { glob } from 'glob';

interface Pattern {
  name: string;
  regex: RegExp;
  suggestion: string;
}

const PATTERNS: Pattern[] = [
  {
    name: 'Language conditional rendering',
    regex: /i18n\.language\s*===\s*['"](?:fr|en)['"]/g,
    suggestion: 'Use useLocalizedField() or useConfigTranslation() instead',
  },
  {
    name: 'Inline ternary for bilingual fields',
    regex: /i18n\.language\s*===\s*['"]fr['"]\s*\?\s*\w+\.(\w+)_fr\s*:\s*\w+\.\1_en/g,
    suggestion: 'Use useLocalizedField().getField(obj, "fieldPrefix")',
  },
  {
    name: 'isFrench variable pattern',
    regex: /const\s+isFrench\s*=\s*i18n\.language\s*===\s*['"]fr['"]/g,
    suggestion: 'Remove and use translation functions directly',
  },
  {
    name: 'Hardcoded Montreal in strings',
    regex: /['"`].*(?:Montreal|Montréal).*['"`]/gi,
    suggestion: 'Use {{config.entityName}} placeholder in translation',
  },
];

interface Match {
  file: string;
  pattern: string;
  occurrences: number;
  suggestion: string;
  examples: string[];
}

function analyzeFile(filePath: string): Match[] {
  const content = fs.readFileSync(filePath, 'utf-8');
  const relativePath = path.relative(process.cwd(), filePath);
  const matches: Match[] = [];

  for (const pattern of PATTERNS) {
    const patternMatches = content.match(pattern.regex);
    if (patternMatches) {
      matches.push({
        file: relativePath,
        pattern: pattern.name,
        occurrences: patternMatches.length,
        suggestion: pattern.suggestion,
        examples: patternMatches.slice(0, 3).map((m) => m.substring(0, 80)),
      });
    }
  }

  return matches;
}

async function main(): Promise<void> {
  console.log('🔍 Scanning for i18n anti-patterns...\n');

  const files = await glob('frontend/src/**/*.{ts,tsx}', {
    ignore: ['**/node_modules/**', '**/*.d.ts'],
  });

  let totalMatches = 0;
  const allMatches: Match[] = [];

  for (const file of files) {
    const matches = analyzeFile(file);
    allMatches.push(...matches);
    totalMatches += matches.reduce((sum, m) => sum + m.occurrences, 0);
  }

  // Group by pattern
  const byPattern = new Map<string, Match[]>();
  for (const match of allMatches) {
    const existing = byPattern.get(match.pattern) || [];
    existing.push(match);
    byPattern.set(match.pattern, existing);
  }

  // Print results
  for (const [pattern, matches] of byPattern) {
    console.log(`\n📌 ${pattern}`);
    console.log(`   Files affected: ${matches.length}`);
    console.log(`   Suggestion: ${matches[0].suggestion}`);
    console.log('   Files:');
    for (const match of matches.slice(0, 10)) {
      console.log(`   - ${match.file} (${match.occurrences} occurrence${match.occurrences > 1 ? 's' : ''})`);
    }
    if (matches.length > 10) {
      console.log(`   ... and ${matches.length - 10} more files`);
    }
  }

  console.log('\n-------------------------------------------');
  console.log(`✅ Scan complete`);
  console.log(`   Total anti-patterns found: ${totalMatches}`);
  console.log(`   Files with issues: ${new Set(allMatches.map((m) => m.file)).size}`);

  if (totalMatches === 0) {
    console.log('\n🎉 No i18n anti-patterns detected!');
  } else {
    console.log('\n⚠️  Run this script after fixing to verify all patterns are resolved.');
  }
}

main().catch(console.error);
