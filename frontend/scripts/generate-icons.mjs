#!/usr/bin/env node
/**
 * Generate PWA icons for manifest.json
 * Run with: node scripts/generate-icons.mjs
 */

import { createCanvas } from '@napi-rs/canvas';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const publicDir = join(__dirname, '..', 'public');
const iconsDir = join(publicDir, 'icons');

// Icon sizes required for PWA
const sizes = [72, 96, 128, 144, 152, 192, 384, 512];

// Brand colors
const PRIMARY_COLOR = '#0066CC';
const DARK_COLOR = '#003366';

function generateIcon(size) {
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Create gradient background
  const gradient = ctx.createLinearGradient(0, 0, size, size);
  gradient.addColorStop(0, PRIMARY_COLOR);
  gradient.addColorStop(1, DARK_COLOR);
  ctx.fillStyle = gradient;

  // Draw rounded rectangle
  const radius = size * 0.15;
  ctx.beginPath();
  ctx.moveTo(radius, 0);
  ctx.lineTo(size - radius, 0);
  ctx.quadraticCurveTo(size, 0, size, radius);
  ctx.lineTo(size, size - radius);
  ctx.quadraticCurveTo(size, size, size - radius, size);
  ctx.lineTo(radius, size);
  ctx.quadraticCurveTo(0, size, 0, size - radius);
  ctx.lineTo(0, radius);
  ctx.quadraticCurveTo(0, 0, radius, 0);
  ctx.closePath();
  ctx.fill();

  // Draw "I" letter
  ctx.fillStyle = 'white';
  ctx.font = `bold ${size * 0.6}px Arial, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('I', size / 2, size / 2 + size * 0.02);

  return canvas;
}

function generateLogoIcon(width, height) {
  const canvas = createCanvas(width, height);
  const ctx = canvas.getContext('2d');

  // Create gradient background
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, PRIMARY_COLOR);
  gradient.addColorStop(1, DARK_COLOR);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  // Draw site name
  ctx.fillStyle = 'white';
  ctx.font = `bold ${height * 0.15}px Arial, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('Idees pour Montreal', width / 2, height / 2 - height * 0.1);

  // Draw tagline
  ctx.font = `${height * 0.06}px Arial, sans-serif`;
  ctx.fillStyle = 'rgba(255,255,255,0.9)';
  ctx.fillText('Partagez vos idees', width / 2, height / 2 + height * 0.1);

  return canvas;
}

// Create icons directory if it doesn't exist
if (!existsSync(iconsDir)) {
  mkdirSync(iconsDir, { recursive: true });
  console.log('Created icons directory:', iconsDir);
}

// Generate PWA icons
console.log('Generating PWA icons...');
for (const size of sizes) {
  const canvas = generateIcon(size);
  const buffer = canvas.toBuffer('image/png');
  const filename = `icon-${size}x${size}.png`;
  const filepath = join(iconsDir, filename);
  writeFileSync(filepath, buffer);
  console.log(`  Created: ${filename}`);
}

// Generate logo.png (512x512 square logo)
console.log('Generating logo.png...');
const logoCanvas = generateIcon(512);
const logoBuffer = logoCanvas.toBuffer('image/png');
writeFileSync(join(publicDir, 'logo.png'), logoBuffer);
console.log('  Created: logo.png');

console.log('\nDone! Icons generated successfully.');
